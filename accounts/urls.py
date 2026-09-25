from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboards
    path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path(
        'admin-dashboard/products/<int:product_id>/<str:action>/',
        views.admin_product_approval_view,
        name='admin_product_approval',
    ),
    path('customer-dashboard/', views.customer_dashboard_view, name='customer_dashboard'),
    path('doctors/<int:provider_id>/', views.doctor_detail_view, name='doctor_detail'),
    path('customer-messages/', views.customer_messages_view, name='customer_messages'),
    path('appointments/book/<int:provider_id>/', views.book_appointment_view, name='book_appointment'),
    path('appointments/<int:appointment_id>/cancel/', views.cancel_appointment_view, name='cancel_appointment'),
    path('seller-dashboard/', views.seller_dashboard_view, name='seller_dashboard'),
    path('seller-messages/', views.seller_messages_view, name='seller_messages'),
    path('provider-dashboard/', views.provider_dashboard_view, name='provider_dashboard'),
    path('courier-dashboard/', views.courier_dashboard_view, name='courier_dashboard'),
    path('dashboard/', views.dashboard_redirect_view, name='dashboard'),
    path('profile/', views.customer_profile_view, name='customer_profile'),
    path('settings/', views.customer_settings_view, name='customer_settings'),

    # Provider pages
    path('provider-profile/', views.provider_profile_view, name='provider_profile'),
    path('provider-appointments/', views.provider_appointments_view, name='provider_appointments'),
    path('provider-messages/', views.provider_messages_view, name='provider_messages'),
    path('provider-patients/', views.provider_patients_view, name='provider_patients'),
]
