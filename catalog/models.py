from django.db import models
from django.utils.text import slugify
from django.conf import settings
from accounts.models import SellerProfile, CustomerProfile, ProviderProfile

class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True, default='')

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Product(models.Model):
    APPROVAL_PENDING = 'pending'
    APPROVAL_APPROVED = 'approved'
    APPROVAL_REJECTED = 'rejected'
    APPROVAL_STATUS_CHOICES = [
        (APPROVAL_PENDING, 'Pending'),
        (APPROVAL_APPROVED, 'Approved'),
        (APPROVAL_REJECTED, 'Rejected'),
    ]

    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    image = models.FileField(upload_to='products/%Y/%m/', blank=True, null=True)
    image_url = models.URLField(max_length=500, blank=True, default='')
    is_regulated = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default=APPROVAL_PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.is_approved = self.approval_status == self.APPROVAL_APPROVED
        update_fields = kwargs.get('update_fields')
        if update_fields and 'approval_status' in update_fields:
            kwargs['update_fields'] = set(update_fields) | {'is_approved'}
        super().save(*args, **kwargs)

    @property
    def display_image(self):
        if self.image:
            return self.image.url
        if self.image_url:
            return self.image_url
        return 'https://placehold.co/400x400/e2e8f0/64748b?text=No+Image'


class ProviderPracticeLocation(models.Model):
    LOCATION_TYPE_CHOICES = [
        ('hospital', 'Hospital'),
        ('clinic', 'Own Clinic'),
        ('online', 'Online'),
    ]

    provider = models.ForeignKey(ProviderProfile, on_delete=models.CASCADE, related_name='practice_locations')
    name = models.CharField(max_length=180)
    address = models.CharField(max_length=255, blank=True)
    location_type = models.CharField(max_length=20, choices=LOCATION_TYPE_CHOICES, default='clinic')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['provider__user__first_name', 'location_type', 'name']

    def __str__(self):
        return f"{self.name} - {self.get_location_type_display()}"


class ProviderAvailabilitySlot(models.Model):
    WEEKDAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    provider = models.ForeignKey(ProviderProfile, on_delete=models.CASCADE, related_name='availability_slots')
    location = models.ForeignKey(ProviderPracticeLocation, on_delete=models.CASCADE, related_name='availability_slots')
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    max_patients = models.PositiveIntegerField(default=12)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['weekday', 'start_time']

    def __str__(self):
        return f"{self.provider} at {self.location} on {self.get_weekday_display()} {self.start_time:%I:%M %p}"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('Scheduled', 'Scheduled'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    patient = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name='appointments', null=True, blank=True)
    provider = models.ForeignKey(ProviderProfile, on_delete=models.CASCADE, related_name='appointments', null=True, blank=True)
    location = models.ForeignKey(ProviderPracticeLocation, on_delete=models.SET_NULL, related_name='appointments', null=True, blank=True)
    slot = models.ForeignKey(ProviderAvailabilitySlot, on_delete=models.SET_NULL, related_name='appointments', null=True, blank=True)
    appointment_mode = models.CharField(max_length=20, choices=[('online', 'Online Visit'), ('offline', 'In-Person Visit')], default='offline')
    appointment_place_name = models.CharField(max_length=180, blank=True)
    appointment_place_address = models.CharField(max_length=255, blank=True)
    serial_number = models.PositiveIntegerField(null=True, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=24, blank=True)
    visit_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    platform_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_due = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ('cash_visit', 'Pay at visit'),
            ('bkash', 'bKash wallet'),
            ('card', 'Visa/Mastercard'),
            ('bank', 'Bank transfer'),
        ],
        default='cash_visit',
    )
    payment_phone = models.CharField(max_length=24, blank=True)
    payment_status = models.CharField(max_length=20, default='Pending')
    scheduled_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Scheduled')
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-scheduled_time']

    def __str__(self):
        return f"Appointment #{self.id} - {self.status}"
