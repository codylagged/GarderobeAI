import cv2
import numpy as np
from sklearn.cluster import KMeans

def get_dominant_color(image_path, k=3):
    """
    Extracts the dominant color from an image using OpenCV and KMeans clustering.
    Returns the RGB color and a human-readable name if possible, and hex.
    """
    try:
        from .tryon_module import remove_background_grabcut
        
        # Load image
        img = cv2.imread(image_path)
        if img is None:
            return "Unknown", "#000000"

        # Resize for faster processing
        img = cv2.resize(img, (150, 150))
        
        # Remove background to isolate clothing
        bgra = remove_background_grabcut(img)
        
        # Extract only non-transparent pixels (RGB)
        pixels = []
        for row in bgra:
            for p in row:
                if p[3] > 50:
                    pixels.append([p[2], p[1], p[0]])
                    
        if not pixels:
            # Fallback if masking failed
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h, w = img_rgb.shape[:2]
            cropped = img_rgb[h//4:3*h//4, w//4:3*w//4]
            pixels = cropped.reshape((-1, 3))
        else:
            pixels = np.array(pixels)
        
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(pixels)

        # Get the most dominant cluster
        counts = np.bincount(kmeans.labels_)
        dominant_cluster = np.argmax(counts)
        dominant_color = kmeans.cluster_centers_[dominant_cluster]

        r, g, b = int(dominant_color[0]), int(dominant_color[1]), int(dominant_color[2])
        hex_color = "#{:02x}{:02x}{:02x}".format(r, g, b)

        # Simple classification of colors based on RGB values
        color_name = classify_color_name(r, g, b)

        return color_name, hex_color
    except Exception as e:
        print(f"Error in dominant color extraction: {e}")
        return "Unknown", "#000000"

def classify_color_name(r, g, b):
    # A very basic rule-based color classifier
    if r > 200 and g > 200 and b > 200:
        return "White"
    if r < 50 and g < 50 and b < 50:
        return "Black"
    if r > 150 and g < 100 and b < 100:
        return "Red"
    if r < 100 and g > 150 and b < 100:
        return "Green"
    if r < 100 and g < 100 and b > 150:
        return "Blue"
    if r > 150 and g > 150 and b < 100:
        return "Yellow"
    if r > 150 and g < 100 and b > 150:
        return "Purple"
    
    # Generic fallback
    if r > g and r > b:
        return "Warm Tone"
    elif b > r and b > g:
        return "Cool Tone"
    else:
        return "Neutral"

def classify_clothing_category(image_path):
    """
    Heuristic clothing category classification based on bounding box aspect ratio.
    """
    try:
        from .tryon_module import remove_background_grabcut
        img = cv2.imread(image_path)
        if img is None:
            return "Shirt"
            
        bgra = remove_background_grabcut(img)
        alpha = bgra[:, :, 3]
        coords = cv2.findNonZero(alpha)
        
        if coords is not None:
            x, y, w, h = cv2.boundingRect(coords)
            aspect_ratio = float(w) / h
            
            if aspect_ratio < 0.6:
                return "Pants"
            elif aspect_ratio > 1.2:
                return "Shoes"
            else:
                # Distinguish between shirt and skirt roughly
                return "Shirt"
    except Exception as e:
        print(f"Category extraction error: {e}")
        
    return "Shirt"

def is_color_pairing_good(hex1, hex2):
    """
    Determines if two colors pair well based on color theory.
    Returns (bool, reason)
    """
    try:
        def hex_to_hsv(hex_str):
            hex_str = hex_str.lstrip('#')
            rgb = np.array([int(hex_str[i:i+2], 16) for i in (0, 2, 4)], dtype=np.uint8)
            # Use OpenCV for conversion
            hsv = cv2.cvtColor(np.uint8([[rgb]]), cv2.COLOR_RGB2HSV)[0][0]
            return hsv # H: 0-180, S: 0-255, V: 0-255

        hsv1 = hex_to_hsv(hex1)
        hsv2 = hex_to_hsv(hex2)

        h1, s1, v1 = float(hsv1[0]), float(hsv1[1]), float(hsv1[2])
        h2, s2, v2 = float(hsv2[0]), float(hsv2[1]), float(hsv2[2])

        # 1. Neutral Rule (White, Black, Gray)
        # Low saturation or extreme value means neutral
        is_neutral1 = s1 < 40 or v1 < 40 or v1 > 220
        is_neutral2 = s2 < 40 or v2 < 40 or v2 > 220

        if is_neutral1 or is_neutral2:
            return True, "Neutral colors go with almost everything."

        # 2. Monochromatic Rule (Same color family)
        hue_diff = abs(h1 - h2)
        if hue_diff < 10:
            return True, "Monochromatic pairing (shades of the same color) is elegant."

        # 3. Analogous Rule (Adjacent on the color wheel)
        # In OpenCV Hue is 0-180, so 30 degrees = 15 units
        if hue_diff < 20:
            return True, "Analogous colors create a harmonious, blended look."

        # 4. Complementary Rule (Opposite on the color wheel)
        # Opposite is 90 units in OpenCV
        if abs(hue_diff - 90) < 15:
            return True, "Complementary colors create a bold, high-contrast look."

        # 5. Contrast Rule (One light, one dark)
        if abs(v1 - v2) > 100:
            return True, "Strong brightness contrast works well for most combinations."

        # Default fallback
        if hue_diff > 45 and hue_diff < 135: # Generally distinct enough
            return True, "The colors have enough distinction to be interesting."

        return False, "The color combination might be a bit clashing."
    except Exception as e:
        print(f"Color theory error: {e}")
        return True, "Colors are always a matter of personal style!"
