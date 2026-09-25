from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User


class Conversation(models.Model):
    """A single thread between two users. One thread per (pair, thread_type) —
    e.g. one customer and one seller only ever share one 'Customer-Seller'
    thread, no matter who messaged first."""

    THREAD_TYPES = [
        ('Customer-Seller', 'Customer-Seller'),
        ('Customer-Provider', 'Customer-Provider'),
        ('Provider-Seller', 'Provider-Seller'),
        ('Seller-Courier', 'Seller-Courier'),
    ]

    participant1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_p1')
    participant2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_p2')
    thread_type = models.CharField(max_length=30, choices=THREAD_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_for_users = models.ManyToManyField(User, blank=True, related_name='hidden_conversations')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['participant1', 'participant2', 'thread_type'],
                name='unique_conversation_pair',
            )
        ]

    def __str__(self):
        return f"{self.thread_type}: {self.participant1.username} & {self.participant2.username}"

    @staticmethod
    def get_or_create_between(user_a, user_b, thread_type):
        """Order-independent lookup: returns the existing thread between these
        two users for this thread_type, or creates one if none exists yet."""
        convo = Conversation.objects.filter(
            Q(participant1=user_a, participant2=user_b) | Q(participant1=user_b, participant2=user_a),
            thread_type=thread_type,
        ).first()
        if convo:
            return convo
        return Conversation.objects.create(
            participant1=user_a, participant2=user_b, thread_type=thread_type
        )


class ChatMessage(models.Model):
    """A single message within a Conversation thread."""

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_chat_messages')
    content = models.TextField(blank=True)
    attachment = models.FileField(upload_to='chat_attachments/%Y/%m/', blank=True, null=True)
    attachment_type = models.CharField(max_length=20, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    deleted_for_users = models.ManyToManyField(User, blank=True, related_name='hidden_chat_messages')

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"ChatMessage from {self.sender.username} in conversation #{self.conversation_id}"

    @property
    def is_image(self):
        return self.attachment_type == 'image'

    @property
    def is_video(self):
        return self.attachment_type == 'video'
