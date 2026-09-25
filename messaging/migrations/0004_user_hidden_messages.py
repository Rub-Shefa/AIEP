from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('messaging', '0003_chatmessage_attachment'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='conversation',
            name='deleted_for_users',
            field=models.ManyToManyField(blank=True, related_name='hidden_conversations', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='deleted_for_users',
            field=models.ManyToManyField(blank=True, related_name='hidden_chat_messages', to=settings.AUTH_USER_MODEL),
        ),
    ]
