from django.db import models
from django.contrib.auth.models import User

class AIQueryLog(models.Model):
    query_text = models.TextField()
    source_interface = models.CharField(max_length=100)
    confidence_score = models.FloatField()
    fallback_triggered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Query Log #{self.id} ({self.confidence_score})"

class Conversation(models.Model):
    THREAD_TYPES = [
        ('Customer-Seller', 'Customer-Seller'),
        ('Customer-Provider', 'Customer-Provider'),
        ('Seller-Courier', 'Seller-Courier'),
    ]
    participant1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_p1')
    participant2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_p2')
    thread_type = models.CharField(max_length=30, choices=THREAD_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.thread_type}: {self.participant1.username} & {self.participant2.username}"

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.sender.username}"