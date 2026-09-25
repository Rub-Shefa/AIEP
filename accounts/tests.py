from datetime import datetime, time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import CustomerProfile, ProviderProfile
from catalog.models import Appointment, ProviderAvailabilitySlot, ProviderPracticeLocation


class AppointmentBookingTests(TestCase):
    def setUp(self):
        self.customer_user = User.objects.create_user(username='patient', password='test-password')
        self.customer = CustomerProfile.objects.create(user=self.customer_user)
        provider_user = User.objects.create_user(
            username='doctor',
            password='test-password',
            first_name='Test',
            last_name='Doctor',
        )
        self.provider = ProviderProfile.objects.create(
            user=provider_user,
            specialty='General Medicine',
            consultation_fee='50.00',
        )
        self.location = ProviderPracticeLocation.objects.create(
            provider=self.provider,
            name='Test Clinic',
            address='Test address',
        )
        self.appointment_date = timezone.localdate() + timedelta(days=7)
        self.slot = ProviderAvailabilitySlot.objects.create(
            provider=self.provider,
            location=self.location,
            weekday=self.appointment_date.weekday(),
            start_time=time(10, 0),
            end_time=time(11, 0),
            max_patients=2,
        )
        naive_dt = datetime.combine(self.appointment_date, self.slot.start_time)
        self.appointment_dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())
        self.client.force_login(self.customer_user)

    def booking_data(self):
        return {
            'appointment_date': self.appointment_date.isoformat(),
            'slot_id': str(self.slot.id),
            'reason_for_visit': 'Checkup',
            'confirm_booking': '1',
            'contact_email': 'patient@example.com',
            'contact_phone': '0123456789',
            'payment_method': 'cash_visit',
        }

    def create_appointment(self, serial_number, status='Scheduled'):
        return Appointment.objects.create(
            patient=self.customer,
            provider=self.provider,
            location=self.location,
            slot=self.slot,
            serial_number=serial_number,
            scheduled_time=self.appointment_dt,
            status=status,
        )

    def test_booking_uses_next_serial_after_cancelled_appointment(self):
        self.create_appointment(1, status='Cancelled')
        self.create_appointment(2)

        response = self.client.post(
            reverse('book_appointment', args=[self.provider.id]),
            self.booking_data(),
        )

        self.assertEqual(response.status_code, 302)
        new_appointment = Appointment.objects.get(serial_number=3)
        self.assertEqual(new_appointment.status, 'Scheduled')

    def test_booking_does_not_exceed_slot_capacity(self):
        self.create_appointment(1)
        self.create_appointment(2)

        response = self.client.post(
            reverse('book_appointment', args=[self.provider.id]),
            self.booking_data(),
        )

        self.assertRedirects(
            response,
            f"{reverse('doctor_detail', args=[self.provider.id])}#book-appointment",
            fetch_redirect_response=False,
        )
        self.assertEqual(Appointment.objects.filter(status='Scheduled').count(), 2)
