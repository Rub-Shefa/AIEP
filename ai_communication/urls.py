from django.urls import path
from . import views

urlpatterns = [
    path('', views.assistant_view, name='ai_assistant'),
    path('clear/', views.clear_chat, name='ai_assistant_clear'),
    path('api/history/', views.api_history, name='ai_assistant_api_history'),
    path('api/message/', views.api_message, name='ai_assistant_api_message'),
]