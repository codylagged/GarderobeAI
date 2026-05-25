from django.urls import path
from .views import RegisterView, UploadClothingView, UserClothingListView, RecommendOutfitView, TryOnView, ClothingItemDeleteView, ClothingItemUpdateView, ProfileView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('upload/', UploadClothingView.as_view(), name='upload_clothing'),
    path('clothes/', UserClothingListView.as_view(), name='user_clothes'),
    path('clothes/<int:pk>/', ClothingItemDeleteView.as_view(), name='delete_clothing'),
    path('clothes/<int:pk>/update/', ClothingItemUpdateView.as_view(), name='update_clothing'),
    path('recommend/', RecommendOutfitView.as_view(), name='recommend_outfit'),
    path('try-on/', TryOnView.as_view(), name='try_on'),
    path('profile/', ProfileView.as_view(), name='profile'),
]
