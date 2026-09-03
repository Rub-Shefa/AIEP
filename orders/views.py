from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from accounts.models import CustomerProfile
from catalog.models import Product
from .cart import Cart
from .models import Order, OrderItem, DeliveryJobPosting, DeliveryBid, Delivery

TAX_SHIPPING_RATE = Decimal('0.05')  # flat 5% tax/shipping surcharge


def _safe_redirect_back(request, fallback):
    """Redirect to wherever the request came from, or a named fallback URL."""
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect(fallback)


@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        quantity = 1
    quantity = max(quantity, 1)

    cart = Cart(request)
    existing_qty = 0
    for item in cart:
        if item['product'].id == product.id:
            existing_qty = item['quantity']
            break

    if existing_qty + quantity > product.stock:
        messages.error(
            request,
            f"Only {product.stock} unit(s) of \"{product.name}\" are available right now."
        )
    else:
        cart.add(product=product, quantity=quantity)
        messages.success(request, f"Added {quantity} x {product.name} to your cart.")

    return _safe_redirect_back(request, reverse('customer_dashboard'))


@login_required
def cart_view(request):
    cart = Cart(request)
    items = list(cart)
    subtotal = cart.get_total_price()
    tax_shipping = (subtotal * TAX_SHIPPING_RATE).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    total = subtotal + tax_shipping
    context = {
        'items': items,
        'subtotal': subtotal,
        'tax_shipping': tax_shipping,
        'total': total,
    }
    return render(request, 'orders/cart.html', context)


@login_required
def update_cart_item(request, product_id):
    if request.method == 'POST':
        cart = Cart(request)
        try:
            quantity = int(request.POST.get('quantity', 1))
        except (TypeError, ValueError):
            quantity = 1

        product = get_object_or_404(Product, id=product_id)
        if quantity > product.stock:
            quantity = product.stock
            messages.warning(request, f"Only {product.stock} unit(s) of \"{product.name}\" available.")

        cart.update(product_id, quantity)
    return redirect('cart_view')


@login_required
def remove_from_cart(request, product_id):
    cart = Cart(request)
    cart.remove(product_id)
    messages.info(request, "Item removed from your cart.")
    return redirect('cart_view')


@login_required
def checkout_view(request):
    if request.method != 'POST':
        return redirect('cart_view')

    cart = Cart(request)
    items = list(cart)

    if not items:
        messages.error(request, "Your cart is empty.")
        return redirect('cart_view')

    # Re-validate stock at checkout time in case it changed since items were added.
    for item in items:
        if item['quantity'] > item['product'].stock:
            messages.error(
                request,
                f"\"{item['product'].name}\" only has {item['product'].stock} unit(s) left. "
                "Please update your cart."
            )
            return redirect('cart_view')

    customer_profile, _ = CustomerProfile.objects.get_or_create(user=request.user)

    subtotal = cart.get_total_price()
    tax_shipping = (subtotal * TAX_SHIPPING_RATE).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    total = subtotal + tax_shipping

    order = Order.objects.create(
        customer=customer_profile,
        subtotal=subtotal,
        tax_shipping=tax_shipping,
        total=total,
        status='Pending',
    )

    for item in items:
        product = item['product']
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=item['quantity'],
            unit_price=item['price'],
        )
        product.stock = max(product.stock - item['quantity'], 0)
        product.save(update_fields=['stock'])

    cart.clear()
    messages.success(request, f"Order #{order.id} placed successfully! We'll keep you posted on its status.")
    return redirect('customer_dashboard')


# --- Courier delivery workflow ---

def _get_courier_profile(request):
    return getattr(request.user, 'courier_profile', None)


@login_required
def place_bid(request, job_id):
    courier_profile = _get_courier_profile(request)
    if courier_profile is None:
        messages.error(request, "Only registered couriers can bid on delivery jobs.")
        return redirect('customer_dashboard')

    job = get_object_or_404(DeliveryJobPosting, id=job_id)

    if request.method != 'POST':
        return redirect('courier_dashboard')

    if not job.is_active or hasattr(job, 'delivery'):
        messages.error(request, "This job is no longer open for bidding.")
        return redirect('courier_dashboard')

    if DeliveryBid.objects.filter(job=job, courier=courier_profile).exists():
        messages.warning(request, "You've already placed a bid on this job.")
        return redirect('courier_dashboard')

    raw_amount = (request.POST.get('bid_amount') or '').strip()
    try:
        bid_amount = Decimal(raw_amount)
    except (InvalidOperation, TypeError):
        messages.error(request, "Enter a valid bid amount.")
        return redirect('courier_dashboard')

    if bid_amount <= 0:
        messages.error(request, "Bid amount must be greater than zero.")
        return redirect('courier_dashboard')

    DeliveryBid.objects.create(job=job, courier=courier_profile, bid_amount=bid_amount)
    messages.success(request, f"Bid of ${bid_amount} placed on Job #{job.id}.")
    return redirect('courier_dashboard')


@login_required
def withdraw_bid(request, bid_id):
    courier_profile = _get_courier_profile(request)
    if courier_profile is None:
        messages.error(request, "Only registered couriers can manage bids.")
        return redirect('customer_dashboard')

    bid = get_object_or_404(DeliveryBid, id=bid_id, courier=courier_profile)

    if bid.status != 'Pending':
        messages.error(request, "Only pending bids can be withdrawn.")
    else:
        job_id = bid.job_id
        bid.delete()
        messages.info(request, f"Bid on Job #{job_id} withdrawn.")
    return redirect('courier_dashboard')


@login_required
def advance_delivery_status(request, delivery_id):
    courier_profile = _get_courier_profile(request)
    if courier_profile is None:
        messages.error(request, "Only registered couriers can update deliveries.")
        return redirect('customer_dashboard')

    delivery = get_object_or_404(Delivery, id=delivery_id, courier=courier_profile)
    flow = [choice[0] for choice in Delivery.STATUS_CHOICES]
    current_index = flow.index(delivery.status)

    if current_index >= len(flow) - 1:
        messages.info(request, "This delivery is already marked as delivered.")
        return redirect('courier_dashboard')

    delivery.status = flow[current_index + 1]
    delivery.save(update_fields=['status', 'updated_at'])

    if delivery.status == 'Delivered':
        order = delivery.job.order
        order.status = 'Completed'
        order.save(update_fields=['status'])
        messages.success(request, f"Delivery #{delivery.id} marked as delivered — Order #{order.id} completed.")
    else:
        messages.success(request, f"Delivery #{delivery.id} updated to \"{delivery.status}\".")

    return redirect('courier_dashboard')


# --- Seller delivery job workflow ---

def _get_seller_profile(request):
    return getattr(request.user, 'seller_profile', None)


@login_required
def seller_post_delivery_job(request, order_id):
    seller_profile = _get_seller_profile(request)
    if seller_profile is None:
        messages.error(request, "Only registered sellers can post delivery jobs.")
        return redirect('seller_dashboard')

    order = get_object_or_404(Order, id=order_id, items__product__seller=seller_profile)

    if request.method != 'POST':
        return redirect('seller_dashboard')

    if hasattr(order, 'deliveryjobposting'):
        messages.warning(request, f"Order #{order.id} already has a delivery job posted.")
        return redirect('seller_dashboard')

    pickup_address = (request.POST.get('pickup_address') or '').strip()
    delivery_address = (request.POST.get('delivery_address') or '').strip()
    raw_pay = (request.POST.get('offered_pay') or '').strip()

    if not pickup_address or not delivery_address:
        messages.error(request, "Pickup and delivery addresses are required.")
        return redirect('seller_dashboard')

    try:
        offered_pay = Decimal(raw_pay)
        if offered_pay <= 0:
            raise InvalidOperation
    except (InvalidOperation, TypeError):
        messages.error(request, "Enter a valid delivery pay amount.")
        return redirect('seller_dashboard')

    DeliveryJobPosting.objects.create(
        seller=seller_profile,
        order=order,
        pickup_address=pickup_address,
        delivery_address=delivery_address,
        offered_pay=offered_pay,
    )
    messages.success(request, f"Delivery job posted for Order #{order.id}. Couriers can now bid on it.")
    return redirect('seller_dashboard')


@login_required
def seller_cancel_job(request, job_id):
    seller_profile = _get_seller_profile(request)
    if seller_profile is None:
        messages.error(request, "Only registered sellers can manage delivery jobs.")
        return redirect('seller_dashboard')

    job = get_object_or_404(DeliveryJobPosting, id=job_id, seller=seller_profile)

    if hasattr(job, 'delivery'):
        messages.error(request, "This job already has an assigned courier and can't be cancelled.")
        return redirect('seller_dashboard')

    if request.method == 'POST':
        order_id = job.order_id
        job.delete()
        messages.info(request, f"Delivery job for Order #{order_id} was cancelled.")
    return redirect('seller_dashboard')


@login_required
def seller_accept_bid(request, bid_id):
    seller_profile = _get_seller_profile(request)
    if seller_profile is None:
        messages.error(request, "Only registered sellers can manage bids.")
        return redirect('seller_dashboard')

    bid = get_object_or_404(DeliveryBid, id=bid_id, job__seller=seller_profile)

    if request.method != 'POST':
        return redirect('seller_dashboard')

    job = bid.job
    if hasattr(job, 'delivery'):
        messages.error(request, "A courier has already been assigned to this job.")
        return redirect('seller_dashboard')

    bid.status = 'Accepted'
    bid.save(update_fields=['status'])
    DeliveryBid.objects.filter(job=job).exclude(id=bid.id).update(status='Rejected')

    Delivery.objects.create(job=job, courier=bid.courier)
    job.is_active = False
    job.save(update_fields=['is_active'])

    order = job.order
    if order.status == 'Pending':
        order.status = 'Processing'
        order.save(update_fields=['status'])

    messages.success(
        request,
        f"Accepted {bid.courier.user.username}'s bid of ${bid.bid_amount} — courier assigned to Order #{order.id}."
    )
    return redirect('seller_dashboard')
