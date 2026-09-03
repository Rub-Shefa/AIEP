from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from .forms import CustomUserCreationForm
from accounts.models import ProviderProfile, CustomerProfile, CourierProfile, SellerProfile
from catalog.models import Category, Product, Appointment

from orders.models import Order, OrderItem, DeliveryJobPosting, DeliveryBid, Delivery
from orders.cart import Cart

def home(request):
    categories = Category.objects.all()
    products = Product.objects.all()
    providers = ProviderProfile.objects.all()
    context = {
        'categories': categories,
        'products': products,
        'providers': providers,
    }
    return render(request, 'accounts/home.html', context)

def is_admin(user):
    return user.is_staff or user.is_superuser

def redirect_based_on_role(user):
    if user.is_staff or user.is_superuser:
        return redirect('admin_dashboard')
    elif hasattr(user, 'seller_profile'):
        return redirect('seller_dashboard')
    elif hasattr(user, 'provider_profile'):
        return redirect('provider_dashboard')
    elif hasattr(user, 'courier_profile'):
        return redirect('courier_dashboard')
    return redirect('customer_dashboard')

def login_view(request):
    if request.user.is_authenticated:
        return redirect_based_on_role(request.user)

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {username}!")
                return redirect_based_on_role(user)
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form})

def register_view(request):
    if request.user.is_authenticated:
        return redirect_based_on_role(request.user)

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully!")
            return redirect_based_on_role(user)
        else:
            # Clean up field names for user messages
            field_name_map = {
                'password1': 'Password',
                'password2': 'Password',
                'phone_number': 'Phone Number',
            }
            for field, errors in form.errors.items():
                display_name = field_name_map.get(field, field.replace('_', ' ').capitalize())
                for error in errors:
                    messages.error(request, f"{display_name}: {error}")
    else:
        form = CustomUserCreationForm()

    return render(request, 'accounts/register.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')

# --- Dashboard Handlers ---
@login_required
@user_passes_test(is_admin)
def admin_dashboard_view(request):
    from ai_communication.models import AIQueryLog

    now = timezone.now()
    week_ago = now - timedelta(days=7)

    # --- Top-line stats ---
    revenue_agg = Order.objects.filter(status='Completed').aggregate(total=Sum('total'))
    total_revenue = revenue_agg['total'] or 0

    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='Pending').count()
    processing_orders = Order.objects.filter(status='Processing').count()
    completed_orders = Order.objects.filter(status='Completed').count()
    cancelled_orders = Order.objects.filter(status='Cancelled').count()

    total_users = User.objects.count()
    new_users_week = User.objects.filter(date_joined__gte=week_ago).count()

    total_customers = CustomerProfile.objects.count()
    total_sellers = SellerProfile.objects.count()
    total_providers = ProviderProfile.objects.count()
    total_couriers = CourierProfile.objects.count()

    total_products = Product.objects.count()
    low_stock_products = Product.objects.filter(stock__lte=5).order_by('stock')[:6]
    low_stock_count = Product.objects.filter(stock__lte=5).count()

    active_deliveries = Delivery.objects.exclude(status='Delivered').count()
    completed_deliveries = Delivery.objects.filter(status='Delivered').count()
    open_delivery_jobs = DeliveryJobPosting.objects.filter(is_active=True, delivery__isnull=True).count()

    ai_logs_total = AIQueryLog.objects.count()
    ai_fallback_count = AIQueryLog.objects.filter(fallback_triggered=True).count()
    ai_fallback_rate = round((ai_fallback_count / ai_logs_total) * 100, 1) if ai_logs_total else 0

    upcoming_appointments = Appointment.objects.filter(
        status='Scheduled', appointment_date__gte=now
    ).count()

    # --- Recent activity ---
    recent_orders = (
        Order.objects.select_related('customer__user')
        .order_by('-created_at')[:8]
    )

    recent_users = User.objects.order_by('-date_joined')[:8]

    # --- Top products by quantity sold ---
    top_products = (
        OrderItem.objects.values('product__name', 'product__stock')
        .annotate(units_sold=Sum('quantity'), revenue=Sum('line_subtotal'))
        .order_by('-units_sold')[:6]
    )

    # --- User management table (with optional role filter) ---
    role_filter = request.GET.get('role', '')
    users_qs = User.objects.select_related(
        'customer_profile', 'seller_profile', 'provider_profile', 'courier_profile'
    ).order_by('-date_joined')

    def role_of(u):
        if u.is_superuser or u.is_staff:
            return 'Admin'
        if hasattr(u, 'seller_profile'):
            return 'Seller'
        if hasattr(u, 'provider_profile'):
            return 'Provider'
        if hasattr(u, 'courier_profile'):
            return 'Courier'
        if hasattr(u, 'customer_profile'):
            return 'Customer'
        return 'Unassigned'

    all_users_with_roles = [{'user': u, 'role': role_of(u)} for u in users_qs]
    if role_filter:
        all_users_with_roles = [row for row in all_users_with_roles if row['role'] == role_filter]

    context = {
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'processing_orders': processing_orders,
        'completed_orders': completed_orders,
        'cancelled_orders': cancelled_orders,
        'total_users': total_users,
        'new_users_week': new_users_week,
        'total_customers': total_customers,
        'total_sellers': total_sellers,
        'total_providers': total_providers,
        'total_couriers': total_couriers,
        'total_products': total_products,
        'low_stock_products': low_stock_products,
        'low_stock_count': low_stock_count,
        'active_deliveries': active_deliveries,
        'completed_deliveries': completed_deliveries,
        'open_delivery_jobs': open_delivery_jobs,
        'ai_logs_total': ai_logs_total,
        'ai_fallback_rate': ai_fallback_rate,
        'upcoming_appointments': upcoming_appointments,
        'recent_orders': recent_orders,
        'recent_users': recent_users,
        'top_products': top_products,
        'all_users_with_roles': all_users_with_roles,
        'role_filter': role_filter,
    }
    return render(request, 'accounts/admin_dashboard.html', context)

@login_required
def customer_dashboard_view(request):
    customer_profile, _ = CustomerProfile.objects.get_or_create(user=request.user)

    categories = Category.objects.all()
    products = Product.objects.select_related('category', 'seller').all().order_by('-created_at')

    selected_category = request.GET.get('category', '')
    query = request.GET.get('q', '').strip()

    if selected_category:
        products = products.filter(category_id=selected_category)
    if query:
        products = products.filter(name__icontains=query)

    orders = (
        Order.objects.filter(customer=customer_profile)
        .prefetch_related('items__product')
        .order_by('-created_at')[:10]
    )

    cart = Cart(request)

    context = {
        'categories': categories,
        'products': products,
        'orders': orders,
        'selected_category': selected_category,
        'query': query,
        'cart_item_count': len(cart),
        'total_orders': Order.objects.filter(customer=customer_profile).count(),
    }
    return render(request, 'accounts/customer_dashboard.html', context)

@login_required
def seller_dashboard_view(request):
    seller_profile = getattr(request.user, 'seller_profile', None)
    if seller_profile is None:
        messages.error(request, "You need a seller profile to access the seller dashboard.")
        return redirect_based_on_role(request.user)

    # --- Product catalog ---
    products = (
        Product.objects.filter(seller=seller_profile)
        .select_related('category')
        .order_by('-created_at')
    )
    total_products = products.count()
    low_stock_products = products.filter(stock__lte=5, stock__gt=0).order_by('stock')
    low_stock_count = low_stock_products.count()
    out_of_stock_count = products.filter(stock=0).count()

    # --- Revenue & order items belonging to this seller ---
    seller_order_items = (
        OrderItem.objects.filter(product__seller=seller_profile)
        .select_related('order', 'product')
    )
    revenue_agg = seller_order_items.filter(order__status='Completed').aggregate(total=Sum('line_subtotal'))
    total_revenue = revenue_agg['total'] or 0

    order_ids = seller_order_items.values_list('order_id', flat=True).distinct()
    seller_orders_qs = (
        Order.objects.filter(id__in=order_ids)
        .select_related('customer__user')
        .prefetch_related('items__product')
        .order_by('-created_at')
    )
    total_orders_count = seller_orders_qs.count()
    pending_orders_count = seller_orders_qs.filter(status='Pending').count()
    processing_orders_count = seller_orders_qs.filter(status='Processing').count()
    completed_orders_count = seller_orders_qs.filter(status='Completed').count()

    posted_order_ids = set(
        DeliveryJobPosting.objects.filter(seller=seller_profile).values_list('order_id', flat=True)
    )

    seller_orders = list(seller_orders_qs[:15])
    for order in seller_orders:
        order.seller_items = [
            item for item in order.items.all() if item.product.seller_id == seller_profile.id
        ]
        order.has_job_posting = order.id in posted_order_ids
        order.needs_delivery = (
            order.status in ('Pending', 'Processing') and not order.has_job_posting
        )

    # --- Delivery jobs posted by this seller ---
    delivery_jobs = (
        DeliveryJobPosting.objects.filter(seller=seller_profile)
        .select_related('order')
        .prefetch_related('bids__courier__user', 'delivery__courier__user')
        .order_by('-id')
    )
    open_jobs = [job for job in delivery_jobs if job.is_active and not hasattr(job, 'delivery')]
    assigned_jobs = [job for job in delivery_jobs if hasattr(job, 'delivery')]

    # --- Top sellers by units moved ---
    top_products = (
        seller_order_items.values('product__name')
        .annotate(units_sold=Sum('quantity'), revenue=Sum('line_subtotal'))
        .order_by('-units_sold')[:5]
    )

    context = {
        'seller_profile': seller_profile,
        'products': products,
        'total_products': total_products,
        'low_stock_products': low_stock_products[:6],
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'total_revenue': total_revenue,
        'seller_orders': seller_orders,
        'total_orders_count': total_orders_count,
        'pending_orders_count': pending_orders_count,
        'processing_orders_count': processing_orders_count,
        'completed_orders_count': completed_orders_count,
        'open_jobs': open_jobs,
        'assigned_jobs': assigned_jobs,
        'top_products': top_products,
    }
    return render(request, 'accounts/seller_dashboard.html', context)

@login_required
def provider_dashboard_view(request):
    provider_profile = getattr(request.user, 'provider_profile', None)
    if provider_profile is None:
        messages.error(request, "You need a provider profile to access the provider dashboard.")
        return redirect_based_on_role(request.user)

    if request.method == 'POST':
        appointment_id = request.POST.get('appointment_id')
        new_status = request.POST.get('status')
        appointment = get_object_or_404(Appointment, id=appointment_id, provider=provider_profile)
        if new_status in dict(Appointment.STATUS_CHOICES):
            appointment.status = new_status
            appointment.save(update_fields=['status'])
            messages.success(request, f"Appointment with {appointment.customer.user.username} marked as {new_status}.")
        return redirect('provider_dashboard')

    now = timezone.now()

    appointments = (
        Appointment.objects.filter(provider=provider_profile)
        .select_related('customer__user')
        .order_by('appointment_date')
    )

    upcoming_appointments = appointments.filter(status='Scheduled', appointment_date__gte=now)
    past_due_appointments = appointments.filter(status='Scheduled', appointment_date__lt=now)
    completed_appointments = appointments.filter(status='Completed').order_by('-appointment_date')
    cancelled_appointments = appointments.filter(status='Cancelled').order_by('-appointment_date')

    total_appointments = appointments.count()
    upcoming_count = upcoming_appointments.count()
    completed_count = completed_appointments.count()
    cancelled_count = cancelled_appointments.count()

    total_earnings = completed_count * provider_profile.consultation_fee

    context = {
        'provider_profile': provider_profile,
        'upcoming_appointments': upcoming_appointments,
        'past_due_appointments': past_due_appointments,
        'completed_appointments': completed_appointments[:10],
        'cancelled_appointments': cancelled_appointments[:10],
        'total_appointments': total_appointments,
        'upcoming_count': upcoming_count,
        'completed_count': completed_count,
        'cancelled_count': cancelled_count,
        'total_earnings': total_earnings,
    }
    return render(request, 'accounts/provider_dashboard.html', context)

@login_required
def courier_dashboard_view(request):
    courier_profile = getattr(request.user, 'courier_profile', None)
    if courier_profile is None:
        messages.error(request, "You need a courier profile to access the courier dashboard.")
        return redirect_based_on_role(request.user)

    if request.method == 'POST' and request.POST.get('action') == 'toggle_availability':
        courier_profile.availability_status = not courier_profile.availability_status
        courier_profile.save(update_fields=['availability_status'])
        messages.success(
            request,
            f"You're now marked as {'available' if courier_profile.availability_status else 'unavailable'} for new jobs."
        )
        return redirect('courier_dashboard')

    already_bid_job_ids = DeliveryBid.objects.filter(courier=courier_profile).values_list('job_id', flat=True)
    available_jobs = (
        DeliveryJobPosting.objects.filter(is_active=True, delivery__isnull=True)
        .exclude(id__in=already_bid_job_ids)
        .select_related('seller', 'order', 'order__customer')
        .order_by('-id')
    )

    my_bids = (
        DeliveryBid.objects.filter(courier=courier_profile)
        .select_related('job', 'job__order')
        .order_by('-id')
    )

    deliveries = (
        Delivery.objects.filter(courier=courier_profile)
        .select_related('job', 'job__order')
        .order_by('-updated_at')
    )
    active_deliveries = deliveries.exclude(status='Delivered')
    completed_deliveries = deliveries.filter(status='Delivered')

    context = {
        'courier_profile': courier_profile,
        'available_jobs': available_jobs,
        'my_bids': my_bids,
        'active_deliveries': active_deliveries,
        'completed_deliveries': completed_deliveries,
        'total_completed': completed_deliveries.count(),
    }
    return render(request, 'accounts/courier_dashboard.html', context)