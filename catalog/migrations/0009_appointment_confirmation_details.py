from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('catalog', '0008_backfill_product_descriptions'),
    ]

    operations = [
        migrations.AddField(
            model_name='appointment',
            name='contact_email',
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name='appointment',
            name='contact_phone',
            field=models.CharField(blank=True, max_length=24),
        ),
        migrations.AddField(
            model_name='appointment',
            name='payment_method',
            field=models.CharField(choices=[('cash_visit', 'Pay at visit'), ('bkash', 'bKash wallet'), ('card', 'Visa/Mastercard'), ('bank', 'Bank transfer')], default='cash_visit', max_length=20),
        ),
        migrations.AddField(
            model_name='appointment',
            name='payment_phone',
            field=models.CharField(blank=True, max_length=24),
        ),
        migrations.AddField(
            model_name='appointment',
            name='payment_status',
            field=models.CharField(default='Pending', max_length=20),
        ),
        migrations.AddField(
            model_name='appointment',
            name='platform_fee',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),
        migrations.AddField(
            model_name='appointment',
            name='total_due',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),
        migrations.AddField(
            model_name='appointment',
            name='visit_fee',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),
    ]
