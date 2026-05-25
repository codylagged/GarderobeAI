from django.db import models
from django.contrib.auth.models import User

class ClothingItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='clothes')
    image = models.ImageField(upload_to='clothing_images/')
    category = models.CharField(max_length=50, blank=True, null=True) # e.g. Shirt, Pants, Dress
    occasion = models.CharField(max_length=50, default='Casual')    # e.g. Casual, Formal, Party
    color = models.CharField(max_length=50, blank=True, null=True)    # e.g. Red, Blue
    hex_color = models.CharField(max_length=10, blank=True, null=True) # e.g. #FF0000
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.category} ({self.color})"

class Recommendation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    items = models.ManyToManyField(ClothingItem)
    occasion = models.CharField(max_length=50) # e.g. Casual, Formal, Party
    reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Recommendation for {self.user.username} - {self.occasion}"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    height = models.FloatField(default=170.0)
    weight = models.FloatField(default=65.0)
    chest = models.FloatField(default=92.0)
    waist = models.FloatField(default=68.0)
    hips = models.FloatField(default=95.0)
    shoulders = models.FloatField(default=40.0)
    legs = models.FloatField(default=80.0)
    skin_tone = models.CharField(max_length=20, default='#eeeeee')
    gender = models.CharField(max_length=10, default='Female', choices=[('Male', 'Male'), ('Female', 'Female')])
    
    def __str__(self):
        return f"Profile for {self.user.username}"
