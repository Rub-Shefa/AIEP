from django.db import models
from accounts.models import CustomerProfile, SellerProfile, CourierProfile
from catalog.models import Product

class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]
    FULFILLMENT_CHOICES = [
        ('delivery', 'Home delivery'),
        ('pickup', 'Store pickup'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('cod', 'Cash on delivery'),
        ('bkash', 'bKash wallet'),
        ('card', 'Visa/Mastercard'),
        ('bank', 'Bank transfer'),
    ]
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name='orders')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax_shipping = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    fulfillment_method = models.CharField(max_length=20, choices=FULFILLMENT_CHOICES, default='delivery')
    delivery_address = models.TextField(blank=True)
    pickup_location = models.CharField(max_length=255, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cod')
    payment_phone = models.CharField(max_length=30, blank=True)
    delivery_note = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.customer.user.username}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        self.line_subtotal = self.unit_price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

class DeliveryJobPosting(models.Model):
    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE)
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    pickup_address = models.TextField()
    delivery_address = models.TextField()
    offered_pay = models.DecimalField(max_digits=8, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Job #{self.id} for Order #{self.order.id}"

class DeliveryBid(models.Model):
    job = models.ForeignKey(DeliveryJobPosting, on_delete=models.CASCADE, related_name='bids')
    courier = models.ForeignKey(CourierProfile, on_delete=models.CASCADE)
    bid_amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, default='Pending') # Pending, Accepted, Rejected

    def __str__(self):
        return f"Bid by {self.courier.user.username} on Job #{self.job.id}"

class Delivery(models.Model):
    STATUS_CHOICES = [
        ('Assigned', 'Assigned'),
        ('Picked Up', 'Picked Up'),
        ('In Transit', 'In Transit'),
        ('Delivered', 'Delivered'),
    ]
    job = models.OneToOneField(DeliveryJobPosting, on_delete=models.CASCADE)
    courier = models.ForeignKey(CourierProfile, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Assigned')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Delivery #{self.id} - {self.status}"
