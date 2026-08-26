from django.db import models
from accounts.models import CustomerProfile, SellerProfile, ProviderProfile

class Category(models.Model):
    name = models.CharField(max_length=100)
    icon_svg = models.TextField(blank=True, help_text="SVG icon code or icon keyword")
    description = models.TextField(blank=True)
    parent_category = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='subcategories'
    )

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Product(models.Model):
    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    dosage = models.CharField(max_length=100, blank=True)
    certifications = models.TextField(blank=True)
    is_regulated = models.BooleanField(default=False)
    image_url = models.URLField(max_length=500, blank=True, default="https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=500")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('Scheduled', 'Scheduled'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name='appointments')
    provider = models.ForeignKey(ProviderProfile, on_delete=models.CASCADE, related_name='appointments')
    appointment_date = models.DateTimeField()
    reason_for_visit = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Scheduled')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Appointment: {self.customer.user.username} with Dr. {self.provider.user.username}"