from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from django.contrib.auth.models import User
from .serializers import UserSerializer, ClothingItemSerializer, RecommendationSerializer
from .models import ClothingItem, Recommendation, Profile
from .ai_module import get_dominant_color, classify_clothing_category
from .tryon_module import generate_virtual_tryon
import os
from django.conf import settings
from django.core.files.storage import default_storage

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = UserSerializer

class UploadClothingView(generics.CreateAPIView):
    queryset = ClothingItem.objects.all()
    serializer_class = ClothingItemSerializer
    permission_classes = (IsAuthenticated,)

    def perform_create(self, serializer):
        item = serializer.save(user=self.request.user)
        # Call AI module to extract color and category
        color_name, hex_color = get_dominant_color(item.image.path)
        
        # Check if user provided an override
        category_override = self.request.data.get('category')
        occasion_override = self.request.data.get('occasion')
        
        if category_override:
            category = category_override
        else:
            category = classify_clothing_category(item.image.path)
        
        # Smart Heuristic for Occasion if not provided
        if not occasion_override:
            if category in ['Shirt', 'Trousers', 'Skirt', 'Blazer']:
                occasion_override = 'Formal'
            elif category in ['Tshirt', 'Lower', 'Jeans']:
                occasion_override = 'Casual'
            else:
                occasion_override = 'Casual'
        
        item.color = color_name
        item.hex_color = hex_color
        item.category = category
        item.occasion = occasion_override
        item.save()

class UserClothingListView(generics.ListAPIView):
    serializer_class = ClothingItemSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return ClothingItem.objects.filter(user=self.request.user)

class ClothingItemDeleteView(generics.DestroyAPIView):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return ClothingItem.objects.filter(user=self.request.user)

class ClothingItemUpdateView(generics.UpdateAPIView):
    serializer_class = ClothingItemSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return ClothingItem.objects.filter(user=self.request.user)

class RecommendOutfitView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        occasion = request.data.get('occasion', 'Casual')
        skin_tone = request.data.get('skin_tone', 'Medium')
        
        user_clothes = ClothingItem.objects.filter(user=request.user)
        if not user_clothes.exists():
            return Response({"error": "No clothes uploaded yet"}, status=400)
            
        # Filter by occasion - STRICT FILTERING
        items_for_occasion = user_clothes.filter(occasion=occasion)
        
        if not items_for_occasion.exists():
            return Response({
                "error": f"Please upload clothes for this occasion to see recommendations."
            }, status=400)
            
        pool = items_for_occasion
        
        from .ai_module import is_color_pairing_good
        import random
        
        # Check for full outfits first (Dresses)
        dresses = list(pool.filter(category='Dress'))
        
        tops = list(pool.filter(category__in=['Shirt', 'Tshirt', 'Jacket', 'Blazer']))
        bottoms = list(pool.filter(category__in=['Pants', 'Trousers', 'Lower', 'Skirt', 'Jeans']))
        
        best_pairing = None
        best_reason = f"Matches your {skin_tone} skin tone and {occasion} vibe."
        
        # Priority 1: A beautiful Dress
        if dresses and random.random() > 0.3: # 70% chance to pick a dress if available
            dress = random.choice(dresses)
            best_pairing = [dress]
            best_reason = f"A stunning {dress.color} dress is the ultimate {occasion} choice!"
        
        # Priority 2: A matched Top + Bottom
        elif tops and bottoms:
            # Try a few random combinations to find a "good" one
            random.shuffle(tops)
            random.shuffle(bottoms)
            
            found_good = False
            for top in tops[:5]:
                for bottom in bottoms[:5]:
                    is_good, reason = is_color_pairing_good(top.hex_color, bottom.hex_color)
                    if is_good:
                        best_pairing = [top, bottom]
                        best_reason = f"{reason} This {top.category} and {bottom.category} combo is perfect for a {occasion} look."
                        found_good = True
                        break
                if found_good: break
            
            if not best_pairing:
                best_pairing = [tops[0], bottoms[0]]
        
        # Fallback: Just one item if nothing else fits
        if not best_pairing:
            if pool.exists():
                item = random.choice(pool)
                best_pairing = [item]
                best_reason = f"This {item.category} is a great piece for your {occasion} outfit."
            else:
                best_pairing = [random.choice(user_clothes)]
            
        rec = Recommendation.objects.create(
            user=request.user, 
            occasion=occasion, 
            reason=best_reason
        )
        if best_pairing:
            rec.items.set(best_pairing)
        
        serializer = RecommendationSerializer(rec)
        return Response(serializer.data)

class TryOnView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user_image = request.FILES.get('user_image')
        clothing_id = request.data.get('clothing_id')
        
        if not user_image or not clothing_id:
            return Response({"error": "user_image and clothing_id are required"}, status=400)
            
        try:
            clothing_item = ClothingItem.objects.get(id=clothing_id, user=request.user)
        except ClothingItem.DoesNotExist:
            return Response({"error": "Clothing item not found"}, status=404)
            
        # Save user image temporarily
        user_img_path = default_storage.save(f"tmp/{user_image.name}", user_image)
        full_user_img_path = os.path.join(settings.MEDIA_ROOT, user_img_path)
        
        output_filename = f"tryon_{request.user.id}_{clothing_id}.jpg"
        output_path = os.path.join(settings.MEDIA_ROOT, 'tryon', output_filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        success = generate_virtual_tryon(full_user_img_path, clothing_item.image.path, output_path, category=clothing_item.category)
        
        # Clean up temp image
        default_storage.delete(user_img_path)
        
        if success:
            tryon_url = f"{settings.MEDIA_URL}tryon/{output_filename}"
            return Response({"tryon_url": tryon_url})
        else:
            return Response({"error": "Failed to generate virtual try-on"}, status=500)

class ProfileView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        profile, created = Profile.objects.get_or_create(user=request.user)
        return Response({
            "height": profile.height,
            "weight": profile.weight,
            "chest": profile.chest,
            "waist": profile.waist,
            "hips": profile.hips,
            "shoulders": profile.shoulders,
            "legs": profile.legs,
            "skin_tone": profile.skin_tone,
            "gender": profile.gender
        })

    def post(self, request):
        profile, created = Profile.objects.get_or_create(user=request.user)
        
        profile.height = request.data.get('height', profile.height)
        profile.weight = request.data.get('weight', profile.weight)
        profile.chest = request.data.get('chest', profile.chest)
        profile.waist = request.data.get('waist', profile.waist)
        profile.hips = request.data.get('hips', profile.hips)
        profile.shoulders = request.data.get('shoulders', profile.shoulders)
        profile.legs = request.data.get('legs', profile.legs)
        profile.skin_tone = request.data.get('skin_tone', profile.skin_tone)
        profile.gender = request.data.get('gender', profile.gender)
        
        profile.save()
        return Response({"message": "Profile updated successfully"})
