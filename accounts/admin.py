from django.contrib import admin
from .models import CustomerProfile, SellerProfile, ProviderProfile, CourierProfile

admin.site.register([CustomerProfile, SellerProfile, ProviderProfile, CourierProfile])