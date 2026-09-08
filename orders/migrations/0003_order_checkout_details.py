from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0002_remove_order_is_subscription_order_tax_shipping_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='delivery_address',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='order',
            name='delivery_note',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='order',
            name='fulfillment_method',
            field=models.CharField(
                choices=[('delivery', 'Home delivery'), ('pickup', 'Store pickup')],
                default='delivery',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_method',
            field=models.CharField(
                choices=[
                    ('cod', 'Cash on delivery'),
                    ('bkash', 'bKash wallet'),
                    ('card', 'Visa/Mastercard'),
                    ('bank', 'Bank transfer'),
                ],
                default='cod',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_phone',
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AddField(
            model_name='order',
            name='pickup_location',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
