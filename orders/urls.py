from django.urls import path
from . import views

urlpatterns = [
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:product_id>/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout_view, name='checkout_view'),
    path('courier/bid/<int:job_id>/', views.place_bid, name='place_bid'),
    path('courier/bid/<int:bid_id>/withdraw/', views.withdraw_bid, name='withdraw_bid'),
    path('courier/delivery/<int:delivery_id>/advance/', views.advance_delivery_status, name='advance_delivery_status'),
    path('seller/orders/<int:order_id>/post-delivery/', views.seller_post_delivery_job, name='seller_post_delivery_job'),
    path('seller/jobs/<int:job_id>/cancel/', views.seller_cancel_job, name='seller_cancel_job'),
    path('seller/bids/<int:bid_id>/accept/', views.seller_accept_bid, name='seller_accept_bid'),
]
