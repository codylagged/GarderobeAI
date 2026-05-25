from rest_framework import serializers
from django.contrib.auth.models import User
from .models import ClothingItem, Recommendation

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        return user

class ClothingItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClothingItem
        fields = '__all__'
        read_only_fields = ('user',)

class RecommendationSerializer(serializers.ModelSerializer):
    items = ClothingItemSerializer(many=True, read_only=True)
    class Meta:
        model = Recommendation
        fields = '__all__'
