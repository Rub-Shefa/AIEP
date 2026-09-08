from django.db import models
from django.contrib.auth.models import User

class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    avatar_image = models.FileField(upload_to='profile_photos/', blank=True)
    avatar_url = models.URLField(max_length=500, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    occupation = models.CharField(max_length=50, blank=True)
    budget_range = models.CharField(max_length=50, blank=True)
    location = models.CharField(max_length=255, blank=True)
    health_preferences = models.TextField(blank=True)

    def __str__(self):
        return f"Customer: {self.user.username}"

class SellerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seller_profile')
    store_name = models.CharField(max_length=255)
    verification_status = models.BooleanField(default=False)

    def __str__(self):
        return self.store_name

class CourierProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='courier_profile')
    vehicle_type = models.CharField(max_length=50)
    service_zone = models.CharField(max_length=100)
    availability_status = models.BooleanField(default=True)

    def __str__(self):
        return f"Courier: {self.user.username}"

class ProviderProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='provider_profile')
    specialty = models.CharField(max_length=100)
    degrees = models.CharField(max_length=255, blank=True, default="MBBS, MD")
    consultation_fee = models.DecimalField(max_digits=8, decimal_places=2, default=50.00)
    experience_years = models.IntegerField(default=5)
    bio = models.TextField(blank=True)
    budget_tier = models.CharField(max_length=50, blank=True)
    consultation_type = models.CharField(max_length=50, default='Online & In-Person')
    credential_status = models.CharField(max_length=50, default='Verified')

    def __str__(self):
        return f"Dr. {self.user.get_full_name() or self.user.username} ({self.specialty})"
