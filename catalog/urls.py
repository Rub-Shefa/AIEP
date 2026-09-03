from django.urls import path
from . import views

urlpatterns = [
    path('add/', views.seller_product_add, name='seller_product_add'),
    path('<int:product_id>/edit/', views.seller_product_edit, name='seller_product_edit'),
    path('<int:product_id>/delete/', views.seller_product_delete, name='seller_product_delete'),
]
