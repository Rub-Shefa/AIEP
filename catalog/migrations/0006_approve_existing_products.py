from django.db import migrations


def approve_existing_products(apps, schema_editor):
    Product = apps.get_model('catalog', 'Product')
    Product.objects.filter(approval_status='pending').update(
        approval_status='approved',
        is_approved=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0005_product_approval_status'),
    ]

    operations = [
        migrations.RunPython(approve_existing_products, migrations.RunPython.noop),
    ]
