from django.contrib import admin
from .models import AIQueryLog, Conversation, Message

admin.site.register([AIQueryLog, Conversation, Message])