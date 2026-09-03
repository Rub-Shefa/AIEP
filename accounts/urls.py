from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboards
    path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('customer-dashboard/', views.customer_dashboard_view, name='customer_dashboard'),
    path('seller-dashboard/', views.seller_dashboard_view, name='seller_dashboard'),
    path('provider-dashboard/', views.provider_dashboard_view, name='provider_dashboard'),
    path('courier-dashboard/', views.courier_dashboard_view, name='courier_dashboard'),

    # Provider pages
    path('provider-profile/', views.provider_profile_view, name='provider_profile'),
    path('provider-appointments/', views.provider_appointments_view, name='provider_appointments'),
    path('provider-messages/', views.provider_messages_view, name='provider_messages'),
    path('provider-patients/', views.provider_patients_view, name='provider_patients'),
]