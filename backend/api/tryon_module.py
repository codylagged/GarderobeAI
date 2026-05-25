import cv2
import numpy as np
import shutil
import os

def generate_virtual_tryon(user_image_path, clothing_image_path, output_path, category="Shirt"):
    """
    Virtual Try-On using state-of-the-art Hugging Face Gradio APIs.
    Routes to OOTDiffusion for bottoms/skirts/dresses and IDM-VTON for tops.
    If the API fails, it falls back to OpenCV GrabCut overlay.
    """
    try:
        from gradio_client import Client, handle_file
        
        # Normalize category
        cat_lower = category.lower()
        
        if any(x in cat_lower for x in ["pants", "skirt", "dress", "trousers", "lower"]):
            print(f"Sending ({category}) to OOTDiffusion API...")
            client = Client("levihsu/OOTDiffusion")
            
            # Determine OOTDiffusion category
            oot_cat = "Lower-body"
            if "dress" in cat_lower:
                oot_cat = "Dress"
            
            result = client.predict(
                vton_img=handle_file(user_image_path),
                garm_img=handle_file(clothing_image_path),
                category=oot_cat,
                n_samples=1,
                n_steps=20,
                image_scale=2.0,
                seed=-1,
                api_name="/process_dc"
            )
            
            # OOTDiffusion returns a Gallery (list of dicts)
            if isinstance(result, list) and len(result) > 0:
                output_image_from_api = result[0]['image']
            else:
                # Fallback if list structure is different
                output_image_from_api = result[0] if isinstance(result, (list, tuple)) else result
        else:
            # Default to IDM-VTON for tops
            print(f"Sending ({category}) to IDM-VTON API...")
            client = Client("yisol/IDM-VTON")
            
            garment_prompt = f"A {category.lower()}"
            
            result = client.predict(
                dict(background=handle_file(user_image_path), layers=[], composite=None),
                garm_img=handle_file(clothing_image_path),
                garment_des=garment_prompt,
                is_checked=True,
                is_checked_crop=False,
                denoise_steps=30,
                seed=42,
                api_name="/tryon"
            )
            
            if isinstance(result, (list, tuple)):
                output_image_from_api = result[0]
            else:
                output_image_from_api = result
            
        shutil.copy(output_image_from_api, output_path)
        print("API Try-On success!")
        return True
        
    except Exception as e:
        print(f"Primary Gradio API failed: {e}")
        try:
            print("Trying secondary Kwai-Kolors API...")
            client = Client("Kwai-Kolors/Kolors-Virtual-Try-On")
            result = client.predict(
                person_img=handle_file(user_image_path),
                garment_img=handle_file(clothing_image_path),
                seed=42,
                api_name="/tryon"
            )
            output_image_from_api = result[0] if isinstance(result, (list, tuple)) else result
            shutil.copy(output_image_from_api, output_path)
            print("Secondary API Try-On success!")
            return True
        except Exception as e2:
            print(f"Secondary API failed: {e2}")
            print("Falling back to OpenCV GrabCut...")
            return fallback_grabcut_tryon(user_image_path, clothing_image_path, output_path, category)

def remove_background_grabcut(img):
    # Aggressive background removal to get rid of white borders
    mask = np.zeros(img.shape[:2], np.uint8)
    bgdModel = np.zeros((1, 65), np.float64)
    fgdModel = np.zeros((1, 65), np.float64)

    h, w = img.shape[:2]
    # Tighter rect to avoid borders
    rect = (15, 15, w - 30, h - 30)

    try:
        cv2.grabCut(img, mask, rect, bgdModel, fgdModel, 7, cv2.GC_INIT_WITH_RECT)
        mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
        
        # Color thresholding to specifically target white/grayish borders
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY_INV)
        mask2 = cv2.bitwise_and(mask2, mask2, mask=thresh)
        
        mask2 = cv2.GaussianBlur(mask2 * 255, (3, 3), 0)
        
        b, g, r = cv2.split(img)
        bgra = cv2.merge((b, g, r, mask2))
        return bgra
    except Exception as e:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        b, g, r = cv2.split(img)
        bgra = cv2.merge((b, g, r, mask))
        return bgra

def fallback_grabcut_tryon(user_image_path, clothing_image_path, output_path, category="Shirt"):
    try:
        user_img = cv2.imread(user_image_path)
        clothing_img = cv2.imread(clothing_image_path)
        
        if user_img is None or clothing_img is None:
            return False

        clothing_bgra = remove_background_grabcut(clothing_img)
        h, w = user_img.shape[:2]
        
        # Scaling based on category
        if "dress" in category.lower():
            c_w = int(w * 0.75) # Dresses need more width
        elif any(x in category.lower() for x in ["pants", "trousers", "lower"]):
            c_w = int(w * 0.6)
        else:
            c_w = int(w * 0.65) # Shirts

        aspect_ratio = clothing_bgra.shape[0] / clothing_bgra.shape[1]
        c_h = int(c_w * aspect_ratio)
        
        # Ensure it's not too tall for the person
        if c_h > h * 0.8:
            c_h = int(h * 0.8)
            c_w = int(c_h / aspect_ratio)

        clothing_resized = cv2.resize(clothing_bgra, (c_w, c_h), interpolation=cv2.INTER_LANCZOS4)
        
        center_x = w // 2
        
        # Better Y positioning
        if any(x in category.lower() for x in ["pants", "trousers", "lower"]):
            # Position pants from the waist down
            top_y = int(h * 0.45)
            center_y = top_y + c_h // 2
        elif "dress" in category.lower():
            # Position dresses from the shoulders down
            top_y = int(h * 0.22) # Lowered to avoid face
            center_y = top_y + c_h // 2
        elif "skirt" in category.lower():
            top_y = int(h * 0.50)
            center_y = top_y + c_h // 2
        else:
            # Position shirts at the torso
            top_y = int(h * 0.20) # Lowered to avoid face
            center_y = top_y + c_h // 2
        
        top_left_x = center_x - c_w // 2
        top_left_y = top_y # Use top-aligned positioning for better accuracy
        
        # Boundary checks
        if top_left_x < 0: top_left_x = 0
        if top_left_y < 0: top_left_y = 0
        if top_left_x + c_w > w: c_w = w - top_left_x
        if top_left_y + c_h > h: c_h = h - top_left_y
        
        clothing_resized = cv2.resize(clothing_resized, (c_w, c_h))

        # Smooth edges of the mask even more for a 'worn' feel
        alpha_mask = clothing_resized[:, :, 3]
        alpha_mask = cv2.GaussianBlur(alpha_mask, (7, 7), 0)
        
        # Create a 3-channel alpha
        alpha = alpha_mask.astype(float) / 255.0
        alpha = np.expand_dims(alpha, axis=2)
        
        roi = user_img[top_left_y:top_left_y+c_h, top_left_x:top_left_x+c_w]
        clothing_bgr = clothing_resized[:, :, :3]
        
        # Apply a 'Worn' effect: Blend with a high alpha but let some shadows through
        # We'll use 90% clothing color and 10% underlying shadows for a more natural look
        blended = (alpha * (clothing_bgr * 0.95 + roi * 0.05) + (1 - alpha) * roi).astype(np.uint8)
        
        # Final pass: check if we can use seamlessClone for even better blending on the edges
        try:
            # We need a center point for seamlessClone
            center = (top_left_x + c_w // 2, top_left_y + c_h // 2)
            # Create a rough mask for the whole clothing
            clone_mask = (alpha_mask > 10).astype(np.uint8) * 255
            # This can be slow but gives a much more 'worn' look
            user_img = cv2.seamlessClone(clothing_bgr, user_img, clone_mask, center, cv2.MIXED_CLONE)
        except:
            # Fallback to standard blending if seamlessClone fails (e.g. at boundaries)
            user_img[top_left_y:top_left_y+c_h, top_left_x:top_left_x+c_w] = blended
        
        cv2.imwrite(output_path, user_img)
        return True
    except Exception as e:
        print(f"Fallback failed: {e}")
        return False
