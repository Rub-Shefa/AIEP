from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_order_checkout_details'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='contact_email',
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name='order',
            name='contact_phone',
            field=models.CharField(blank=True, max_length=30),
        ),
    ]
