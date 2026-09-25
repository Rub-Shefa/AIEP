from datetime import time

from django.db import migrations, models
import django.db.models.deletion


def seed_provider_booking_defaults(apps, schema_editor):
    ProviderProfile = apps.get_model('accounts', 'ProviderProfile')
    ProviderPracticeLocation = apps.get_model('catalog', 'ProviderPracticeLocation')
    ProviderAvailabilitySlot = apps.get_model('catalog', 'ProviderAvailabilitySlot')

    for provider in ProviderProfile.objects.all():
        provider_name = ' '.join(
            part for part in (provider.user.first_name, provider.user.last_name)
            if part
        ) or provider.user.username
        online, _ = ProviderPracticeLocation.objects.get_or_create(
            provider=provider,
            name='HealthFlow Online Consultation',
            defaults={
                'address': 'Secure video visit through HealthFlow',
                'location_type': 'online',
                'is_active': True,
            },
        )
        clinic, _ = ProviderPracticeLocation.objects.get_or_create(
            provider=provider,
            name=f"Dr. {provider_name}'s Clinic",
            defaults={
                'address': 'Clinic address to be confirmed by provider',
                'location_type': 'clinic',
                'is_active': True,
            },
        )
        for location, weekday, start, end, max_patients in [
            (online, 1, time(19, 0), time(21, 0), 10),
            (clinic, 5, time(10, 0), time(13, 0), 15),
        ]:
            ProviderAvailabilitySlot.objects.get_or_create(
                provider=provider,
                location=location,
                weekday=weekday,
                start_time=start,
                defaults={
                    'end_time': end,
                    'max_patients': max_patients,
                    'is_active': True,
                },
            )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_remove_product_category_delete_category_and_more'),
        ('catalog', '0006_approve_existing_products'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProviderPracticeLocation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=180)),
                ('address', models.CharField(blank=True, max_length=255)),
                ('location_type', models.CharField(choices=[('hospital', 'Hospital'), ('clinic', 'Own Clinic'), ('online', 'Online')], default='clinic', max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('provider', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='practice_locations', to='accounts.providerprofile')),
            ],
            options={
                'ordering': ['provider__user__first_name', 'location_type', 'name'],
            },
        ),
        migrations.CreateModel(
            name='ProviderAvailabilitySlot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('weekday', models.PositiveSmallIntegerField(choices=[(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')])),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('max_patients', models.PositiveIntegerField(default=12)),
                ('is_active', models.BooleanField(default=True)),
                ('location', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='availability_slots', to='catalog.providerpracticelocation')),
                ('provider', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='availability_slots', to='accounts.providerprofile')),
            ],
            options={
                'ordering': ['weekday', 'start_time'],
            },
        ),
        migrations.AddField(
            model_name='appointment',
            name='appointment_mode',
            field=models.CharField(choices=[('online', 'Online Visit'), ('offline', 'In-Person Visit')], default='offline', max_length=20),
        ),
        migrations.AddField(
            model_name='appointment',
            name='appointment_place_address',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='appointment',
            name='appointment_place_name',
            field=models.CharField(blank=True, max_length=180),
        ),
        migrations.AddField(
            model_name='appointment',
            name='serial_number',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='appointment',
            name='location',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='appointments', to='catalog.providerpracticelocation'),
        ),
        migrations.AddField(
            model_name='appointment',
            name='slot',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='appointments', to='catalog.provideravailabilityslot'),
        ),
        migrations.RunPython(seed_provider_booking_defaults, migrations.RunPython.noop),
    ]
