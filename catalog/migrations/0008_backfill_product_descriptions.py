from django.db import migrations


PRODUCT_DESCRIPTIONS = {
    'Cough Pill': 'Over-the-counter cough relief tablets for temporary support of common cough symptoms. Follow the package directions and ask a pharmacist if you take other medicines.',
    'Sleeping pills': 'Sleep-support product intended for short-term use only. Consult a qualified healthcare professional before use, especially with other medicines or health conditions.',
    'Paracetamol 500mg Extra': 'Pain and fever relief tablets. Check the active ingredients and package directions, and consult a pharmacist before use.',
    'Amoxicillin 250mg Capsules': 'Prescription antibiotic capsules used only when prescribed for a confirmed bacterial infection. Complete the prescribed course and do not self-medicate.',
    'Organic Vitamin C 1000mg': 'Vitamin C supplement for daily nutritional support. Use according to the label and ask a healthcare professional about suitable intake.',
    'Omega-3 Fish Oil 1200mg': 'Fish oil supplement containing omega-3 fatty acids for general nutritional support. Check interactions before use, especially with blood thinners.',
    'Digital Blood Pressure Monitor': 'Home blood pressure monitor with a digital reading display for tracking measurements. Use the correct cuff size and discuss readings with a healthcare professional.',
}


def backfill_descriptions(apps, schema_editor):
    Product = apps.get_model('catalog', 'Product')
    for name, description in PRODUCT_DESCRIPTIONS.items():
        Product.objects.filter(name=name, description='').update(description=description)


class Migration(migrations.Migration):
    dependencies = [
        ('catalog', '0007_provider_locations_appointment_details'),
    ]

    operations = [
        migrations.RunPython(backfill_descriptions, migrations.RunPython.noop),
    ]
