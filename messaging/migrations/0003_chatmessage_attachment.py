from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('messaging', '0002_delete_aiquerylog_alter_chatmessage_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chatmessage',
            name='content',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='attachment',
            field=models.FileField(blank=True, null=True, upload_to='chat_attachments/%Y/%m/'),
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='attachment_type',
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
