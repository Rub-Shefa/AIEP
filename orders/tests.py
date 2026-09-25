from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import SellerProfile
from catalog.models import Category, Product
from orders.models import Order


class CheckoutApprovalTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(username='customer', password='test-password')
        seller_user = User.objects.create_user(username='seller', password='test-password')
        seller = SellerProfile.objects.create(user=seller_user, store_name='Test Store')
        category = Category.objects.create(name='Medicine')
        self.product = Product.objects.create(
            seller=seller,
            category=category,
            name='Test Product',
            price='12.50',
            stock=5,
            approval_status=Product.APPROVAL_APPROVED,
        )
        self.client.force_login(self.customer)

    def test_checkout_rejects_product_that_lost_approval(self):
        self.client.post(reverse('add_to_cart', args=[self.product.id]), {'quantity': 2})
        self.product.approval_status = Product.APPROVAL_REJECTED
        self.product.save(update_fields=['approval_status'])

        response = self.client.post(reverse('checkout_view'), {
            'contact_email': 'customer@example.com',
            'contact_phone': '0123456789',
            'fulfillment_method': 'delivery',
            'delivery_address': 'Test address',
            'payment_method': 'cod',
        })

        self.assertRedirects(response, reverse('cart_view'))
        self.assertFalse(Order.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
