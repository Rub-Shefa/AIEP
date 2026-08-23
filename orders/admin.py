from django.contrib import admin
from .models import Order, OrderItem, DeliveryJobPosting, DeliveryBid, Delivery

admin.site.register([Order, OrderItem, DeliveryJobPosting, DeliveryBid, Delivery])