from django.urls import path
from . import views

urlpatterns = [
    path('seller/products/add/', views.seller_product_add, name='seller_product_add'),
    path('seller/products/<int:pk>/edit/', views.seller_product_edit, name='seller_product_edit'),
    path('seller/products/<int:pk>/delete/', views.seller_product_delete, name='seller_product_delete'),
]