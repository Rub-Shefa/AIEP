from django.db import migrations, models


def backfill_approval_status(apps, schema_editor):
    Product = apps.get_model('catalog', 'Product')
    Product.objects.filter(is_approved=True).update(approval_status='approved')
    Product.objects.filter(is_approved=False).update(approval_status='pending')


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0004_alter_appointment_options_alter_category_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='approval_status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('approved', 'Approved'),
                    ('rejected', 'Rejected'),
                ],
                default='pending',
                max_length=20,
            ),
        ),
        migrations.RunPython(backfill_approval_status, migrations.RunPython.noop),
    ]
