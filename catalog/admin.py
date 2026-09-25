from django.contrib import admin
from .models import Category, Product, ProviderPracticeLocation, ProviderAvailabilitySlot

admin.site.register(Category)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'seller', 'category', 'price', 'stock', 'approval_status', 'is_approved')
    list_filter = ('approval_status', 'is_regulated', 'category')
    search_fields = ('name', 'seller__store_name', 'seller__user__username')


@admin.register(ProviderPracticeLocation)
class ProviderPracticeLocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider', 'location_type', 'is_active')
    list_filter = ('location_type', 'is_active')
    search_fields = ('name', 'address', 'provider__user__username', 'provider__user__first_name', 'provider__user__last_name')


@admin.register(ProviderAvailabilitySlot)
class ProviderAvailabilitySlotAdmin(admin.ModelAdmin):
    list_display = ('provider', 'location', 'weekday', 'start_time', 'end_time', 'max_patients', 'is_active')
    list_filter = ('weekday', 'location__location_type', 'is_active')
