from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
from datetime import datetime, timedelta
import base64
from binascii import Error as BinasciiError
from django.core.files.base import ContentFile
from .forms import CustomUserCreationForm, CustomerAccountForm, CustomerProfileForm, CustomerSettingsAccountForm
from accounts.models import ProviderProfile, CustomerProfile, CourierProfile, SellerProfile
from catalog.models import Category, Product, Appointment
from messaging.models import Conversation, ChatMessage
from orders.models import Order, OrderItem, DeliveryJobPosting, DeliveryBid, Delivery
from orders.cart import Cart

def home(request):
    categories = Category.objects.all()
    providers = ProviderProfile.objects.all()

    search_query = request.GET.get('q', '').strip()
    ai_search_used = False

    if search_query:
        # Pass 1: exact/partial keyword match (fast, no AI call).
        products = Product.objects.filter(
            Q(name__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(dosage__icontains=search_query)
        ).select_related('category')

        # Pass 2: nothing matched by keyword -> ask the AI to reason about
        # the catalog semantically (e.g. "headache" -> "Paracetamol").
        if not products.exists():
            from ai_communication.ai_search import ai_semantic_product_search
            all_products = Product.objects.select_related('category').all()
            products = ai_semantic_product_search(search_query, all_products)
            ai_search_used = bool(products)
    else:
        products = Product.objects.all()

    context = {
        'categories': categories,
        'products': products,
        'providers': providers,
        'search_query': search_query,
        'ai_search_used': ai_search_used,
    }
    return render(request, 'accounts/home.html', context)


@login_required
def dashboard_redirect_view(request):
    """Single generic 'go to my dashboard' link that works for every role,
    so templates never need to know which specific dashboard a user belongs to."""
    return redirect_based_on_role(request.user)

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


def _safe_customer_next(request):
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return next_url
    return None


def login_view(request):
    if request.user.is_authenticated:
        next_url = _safe_customer_next(request)
        if next_url and not (request.user.is_staff or request.user.is_superuser):
            return redirect(next_url)
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
                next_url = _safe_customer_next(request)
                if next_url and not (user.is_staff or user.is_superuser):
                    return redirect(next_url)
                return redirect_based_on_role(user)
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form, 'next': request.GET.get('next', '')})

def register_view(request):
    if request.user.is_authenticated:
        next_url = _safe_customer_next(request)
        if next_url and not (request.user.is_staff or request.user.is_superuser):
            return redirect(next_url)
        return redirect_based_on_role(request.user)

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully!")
            next_url = _safe_customer_next(request)
            if next_url and not (user.is_staff or user.is_superuser):
                return redirect(next_url)
            return redirect_based_on_role(user)
        else:
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

    return render(request, 'accounts/register.html', {'form': form, 'next': request.GET.get('next', '')})

def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('login')

# --- Dashboard Handlers ---

@login_required
@user_passes_test(is_admin)
def admin_dashboard_view(request):
    from ai_communication.models import AIQueryLog
    from django.db.models.functions import TruncDate
    import json

    now = timezone.now()
    week_ago = now - timedelta(days=7)

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

    recent_orders = (
        Order.objects.select_related('customer__user')
        .order_by('-created_at')[:8]
    )

    recent_users = User.objects.order_by('-date_joined')[:8]

    top_products = (
        OrderItem.objects.values('product__name', 'product__stock')
        .annotate(units_sold=Sum('quantity'), revenue=Sum('line_subtotal'))
        .order_by('-units_sold')[:6]
    )

    # ---- Real, DB-driven chart data (no hardcoded numbers) ----

    # 1. Orders & revenue trend for the last 7 days
    today = timezone.localdate()
    start_date = today - timedelta(days=6)
    daily_rows = (
        Order.objects.filter(created_at__date__gte=start_date)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(order_count=Count('id'), revenue=Sum('total'))
        .order_by('day')
    )
    daily_map = {row['day']: row for row in daily_rows}
    trend_labels, trend_order_counts, trend_revenue = [], [], []
    for i in range(7):
        d = start_date + timedelta(days=i)
        trend_labels.append(d.strftime('%a'))
        row = daily_map.get(d)
        trend_order_counts.append(row['order_count'] if row else 0)
        trend_revenue.append(float(row['revenue']) if row and row['revenue'] else 0.0)

    # 2. New user signups for the last 7 days
    daily_user_rows = (
        User.objects.filter(date_joined__date__gte=start_date)
        .annotate(day=TruncDate('date_joined'))
        .values('day')
        .annotate(signup_count=Count('id'))
        .order_by('day')
    )
    daily_user_map = {row['day']: row['signup_count'] for row in daily_user_rows}
    signup_counts = [daily_user_map.get(start_date + timedelta(days=i), 0) for i in range(7)]

    # 3. Order status breakdown (donut)
    order_status_labels = ['Pending', 'Processing', 'Completed', 'Cancelled']
    order_status_values = [pending_orders, processing_orders, completed_orders, cancelled_orders]

    # 4. User role breakdown (donut)
    role_labels = ['Customers', 'Sellers', 'Providers', 'Couriers']
    role_values = [total_customers, total_sellers, total_providers, total_couriers]

    # 5. Top products (bar)
    top_products_list = list(top_products)
    top_product_labels = [p['product__name'] for p in top_products_list]
    top_product_units = [p['units_sold'] for p in top_products_list]

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
        # Chart data, pre-serialized to JSON so the template can drop it
        # straight into <script> without extra template-side formatting.
        'trend_labels_json': json.dumps(trend_labels),
        'trend_order_counts_json': json.dumps(trend_order_counts),
        'trend_revenue_json': json.dumps(trend_revenue),
        'signup_counts_json': json.dumps(signup_counts),
        'order_status_labels_json': json.dumps(order_status_labels),
        'order_status_values_json': json.dumps(order_status_values),
        'role_labels_json': json.dumps(role_labels),
        'role_values_json': json.dumps(role_values),
        'top_product_labels_json': json.dumps(top_product_labels),
        'top_product_units_json': json.dumps(top_product_units),
    }
    return render(request, 'accounts/admin/admin_dashboard.html', context)

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

    # Browse Doctors — pulled straight from ProviderProfile, filterable by
    # specialty and free-text search, nothing hardcoded.
    doctors = ProviderProfile.objects.select_related('user').all().order_by('-experience_years')
    specialties = (
        ProviderProfile.objects.exclude(specialty='')
        .order_by('specialty')
        .values_list('specialty', flat=True)
        .distinct()
    )

    selected_specialty = request.GET.get('specialty', '')
    doctor_query = request.GET.get('doctor_q', '').strip()

    if selected_specialty:
        doctors = doctors.filter(specialty=selected_specialty)
    if doctor_query:
        doctors = doctors.filter(
            Q(user__first_name__icontains=doctor_query)
            | Q(user__last_name__icontains=doctor_query)
            | Q(specialty__icontains=doctor_query)
        )

    orders = (
        Order.objects.filter(customer=customer_profile)
        .prefetch_related('items__product')
        .order_by('-created_at')[:10]
    )

    # My Appointments — real bookings against the Appointment model, split
    # into what's still coming up vs. what's already happened or was cancelled.
    now = timezone.now()
    all_appointments = (
        Appointment.objects.filter(customer=customer_profile)
        .select_related('provider__user')
        .order_by('appointment_date')
    )
    upcoming_appointments = all_appointments.filter(status='Scheduled', appointment_date__gte=now)
    past_appointments = (
        all_appointments.exclude(status='Scheduled', appointment_date__gte=now)
        .order_by('-appointment_date')[:10]
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
        'customer_profile': customer_profile,
        'doctors': doctors,
        'specialties': specialties,
        'selected_specialty': selected_specialty,
        'doctor_query': doctor_query,
        'total_doctors': ProviderProfile.objects.count(),
        'upcoming_appointments': upcoming_appointments,
        'past_appointments': past_appointments,
        'upcoming_appointments_count': upcoming_appointments.count(),
        'today_str': now.strftime('%Y-%m-%d'),
    }
    return render(request, 'accounts/customer/customer_dashboard.html', context)


@login_required
def customer_profile_view(request):
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        account_form = CustomerAccountForm(request.POST, instance=request.user)
        profile_form = CustomerProfileForm(request.POST, request.FILES, instance=profile)
        if account_form.is_valid() and profile_form.is_valid():
            account_form.save()
            profile = profile_form.save(commit=False)
            if request.POST.get('remove_avatar') == '1':
                if profile.avatar_image:
                    profile.avatar_image.delete(save=False)
                profile.avatar_image = ''
                profile.avatar_url = ''
            else:
                crop_data = request.POST.get('avatar_crop', '')
                if crop_data.startswith('data:image/'):
                    try:
                        _, encoded = crop_data.split(',', 1)
                        profile.avatar_image.save(
                            f'{request.user.username}-profile.png',
                            ContentFile(base64.b64decode(encoded, validate=True)),
                            save=False,
                        )
                        profile.avatar_url = ''
                    except (ValueError, BinasciiError):
                        messages.error(request, 'That cropped image could not be processed.')
            profile.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('customer_profile')
    else:
        account_form = CustomerAccountForm(instance=request.user)
        profile_form = CustomerProfileForm(instance=profile)
    return render(request, 'accounts/customer/profile.html', {
        'account_form': account_form,
        'profile_form': profile_form,
        'customer_profile': profile,
    })


@login_required
def customer_settings_view(request):
    CustomerProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        account_form = CustomerSettingsAccountForm(request.POST, instance=request.user)
        password_form = PasswordChangeForm(request.user, request.POST)
        action = request.POST.get('action')

        if action == 'account' and account_form.is_valid():
            account_form.save()
            messages.success(request, 'Your account settings have been saved.')
            return redirect('customer_settings')

        if action == 'password' and password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password has been updated.')
            return redirect('customer_settings')
    else:
        account_form = CustomerSettingsAccountForm(instance=request.user)
        password_form = PasswordChangeForm(request.user)
    for field in password_form.fields.values():
        field.widget.attrs.update({
            'class': 'w-full rounded-xl border border-slate-300 px-4 py-2.5 text-sm bg-white focus:ring-2 focus:ring-teal/30 focus:border-teal outline-none transition-all'
        })
    return render(request, 'accounts/customer/settings.html', {
        'account_form': account_form,
        'password_form': password_form,
    })


@login_required
def book_appointment_view(request, provider_id):
    """Customer-side booking: creates a real Appointment row against the
    chosen provider, with basic conflict and past-date checks."""
    if request.method != 'POST':
        return redirect('customer_dashboard')

    customer_profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
    provider = get_object_or_404(ProviderProfile, id=provider_id)
    redirect_target = f"{reverse('customer_dashboard')}#doctors"

    date_str = request.POST.get('appointment_date', '').strip()
    time_str = request.POST.get('appointment_time', '').strip()
    reason = request.POST.get('reason_for_visit', '').strip()

    if not date_str or not time_str:
        messages.error(request, "Please choose both a date and a time for your appointment.")
        return redirect(redirect_target)

    try:
        naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        messages.error(request, "That date or time didn't look right — please try again.")
        return redirect(redirect_target)

    appointment_dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())
    doctor_name = provider.user.get_full_name() or provider.user.username

    if appointment_dt < timezone.now():
        messages.error(request, "You can't book an appointment in the past.")
        return redirect(redirect_target)

    slot_taken = Appointment.objects.filter(
        provider=provider,
        appointment_date=appointment_dt,
        status='Scheduled',
    ).exists()
    if slot_taken:
        messages.error(
            request,
            f"Dr. {doctor_name} already has a booking at that exact time. Please choose another slot."
        )
        return redirect(redirect_target)

    Appointment.objects.create(
        customer=customer_profile,
        provider=provider,
        appointment_date=appointment_dt,
        reason_for_visit=reason,
        status='Scheduled',
    )
    messages.success(
        request,
        f"Appointment booked with Dr. {doctor_name} on {appointment_dt.strftime('%b %d, %Y at %I:%M %p')}."
    )
    return redirect(f"{reverse('customer_dashboard')}#appointments")


@login_required
def cancel_appointment_view(request, appointment_id):
    """Lets a customer cancel their own upcoming appointment."""
    if request.method != 'POST':
        return redirect('customer_dashboard')

    customer_profile = getattr(request.user, 'customer_profile', None)
    appointment = get_object_or_404(Appointment, id=appointment_id, customer=customer_profile)

    if appointment.status == 'Scheduled':
        appointment.status = 'Cancelled'
        appointment.save(update_fields=['status'])
        messages.success(request, "Your appointment has been cancelled.")
    else:
        messages.error(request, "This appointment can no longer be cancelled.")

    return redirect(f"{reverse('customer_dashboard')}#appointments")

@login_required
def seller_dashboard_view(request):
    seller_profile = getattr(request.user, 'seller_profile', None)
    if seller_profile is None:
        messages.error(request, "You need a seller profile to access the seller dashboard.")
        return redirect_based_on_role(request.user)

    products = (
        Product.objects.filter(seller=seller_profile)
        .select_related('category')
        .order_by('-created_at')
    )
    total_products = products.count()
    low_stock_products = products.filter(stock__lte=5, stock__gt=0).order_by('stock')
    low_stock_count = low_stock_products.count()
    out_of_stock_count = products.filter(stock=0).count()

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

    # Order History filter — practical status filter so a seller with a long
    # history can actually find what they're looking for.
    order_status_filter = request.GET.get('order_status', '').strip()
    if order_status_filter in dict(Order.STATUS_CHOICES):
        seller_orders_qs = seller_orders_qs.filter(status=order_status_filter)

    posted_order_ids = set(
        DeliveryJobPosting.objects.filter(seller=seller_profile).values_list('order_id', flat=True)
    )

    seller_orders = list(seller_orders_qs[:20])
    for order in seller_orders:
        order.seller_items = [
            item for item in order.items.all() if item.product.seller_id == seller_profile.id
        ]
        order.has_job_posting = order.id in posted_order_ids
        order.needs_delivery = (
            order.status in ('Pending', 'Processing') and not order.has_job_posting
        )

    delivery_jobs = (
        DeliveryJobPosting.objects.filter(seller=seller_profile)
        .select_related('order')
        .prefetch_related('bids__courier__user', 'delivery__courier__user')
        .order_by('-id')
    )
    open_jobs = [job for job in delivery_jobs if job.is_active and not hasattr(job, 'delivery')]
    assigned_jobs = [job for job in delivery_jobs if hasattr(job, 'delivery')]

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
        'order_status_filter': order_status_filter,
        'order_status_choices': Order.STATUS_CHOICES,
        'open_jobs': open_jobs,
        'assigned_jobs': assigned_jobs,
        'top_products': top_products,
    }
    return render(request, 'accounts/seller/seller_dashboard.html', context)

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
    return render(request, 'accounts/provider/provider_dashboard.html', context)

@login_required
def provider_profile_view(request):
    provider_profile, _ = ProviderProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        if full_name:
            names = full_name.split(' ', 1)
            request.user.first_name = names[0]
            request.user.last_name = names[1] if len(names) > 1 else ''
            request.user.save()

        provider_profile.specialization = request.POST.get('specialization', '')
        consultation_fee = request.POST.get('consultation_fee')
        if consultation_fee:
            provider_profile.consultation_fee = consultation_fee
        provider_profile.bio = request.POST.get('bio', '')
        provider_profile.save()

        messages.success(request, "Profile updated successfully.")
        return redirect('provider_profile')

    context = {
        'provider': provider_profile,
    }
    return render(request, 'accounts/provider/provider_profile.html', context)

@login_required
def provider_appointments_view(request):
    provider_profile = getattr(request.user, 'provider_profile', None)
    if provider_profile is None:
        messages.error(request, "You need a provider profile to access appointments.")
        return redirect_based_on_role(request.user)

    if request.method == 'POST':
        appointment_id = request.POST.get('appointment_id')
        new_status = request.POST.get('status')
        appointment = get_object_or_404(Appointment, id=appointment_id, provider=provider_profile)
        if new_status in dict(Appointment.STATUS_CHOICES):
            appointment.status = new_status
            appointment.save(update_fields=['status'])
            messages.success(request, f"Appointment status updated to {new_status}.")
        return redirect('provider_appointments')

    appointments = (
        Appointment.objects.filter(provider=provider_profile)
        .select_related('customer__user')
        .order_by('-appointment_date')
    )

    context = {
        'appointments': appointments,
    }
    return render(request, 'accounts/provider/provider_appointments.html', context)


@login_required
def provider_messages_view(request):
    provider_profile = getattr(request.user, 'provider_profile', None)
    if provider_profile is None:
        messages.error(request, "You need a provider profile to access messages.")
        return redirect_based_on_role(request.user)

    # Fetch distinct patients who have booked appointments with this provider
    patients = (
        CustomerProfile.objects.filter(appointments__provider=provider_profile)
        .distinct()
        .select_related('user')
    )

    selected_patient_id = request.GET.get('patient_id')
    selected_patient = None
    chat_messages = []

    if selected_patient_id:
        selected_patient = get_object_or_404(CustomerProfile, id=selected_patient_id)

        # One thread per (provider, patient) pair — created on first contact,
        # reused after that regardless of who sent the first message.
        conversation = Conversation.get_or_create_between(
            request.user, selected_patient.user, thread_type='Customer-Provider'
        )

        if request.method == 'POST':
            body = request.POST.get('message', '').strip()
            if body:
                ChatMessage.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    content=body,
                )
                messages.success(request, "Message sent successfully.")
                return redirect(f"{request.path}?patient_id={selected_patient_id}")

        chat_messages = (
            conversation.messages
            .select_related('sender')
            .order_by('timestamp')
        )

    context = {
        'patients': patients,
        'selected_patient': selected_patient,
        'chat_messages': chat_messages,
    }
    return render(request, 'accounts/provider/provider_messages.html', context)


@login_required
def provider_patients_view(request):
    provider_profile = getattr(request.user, 'provider_profile', None)
    if provider_profile is None:
        messages.error(request, "You need a provider profile to access patient records.")
        return redirect_based_on_role(request.user)

    appointments = (
        Appointment.objects.filter(provider=provider_profile)
        .select_related('customer__user')
        .order_by('customer_id', '-appointment_date')
    )

    # Group this provider's appointments by patient, newest visit first.
    patients_map = {}
    for appt in appointments:
        cust_id = appt.customer_id
        entry = patients_map.setdefault(cust_id, {
            'customer': appt.customer,
            'appointments': [],
            'total_visits': 0,
            'last_visit': None,
        })
        entry['appointments'].append(appt)
        entry['total_visits'] += 1
        if entry['last_visit'] is None or appt.appointment_date > entry['last_visit']:
            entry['last_visit'] = appt.appointment_date

    patients = sorted(
        patients_map.values(),
        key=lambda p: p['last_visit'] or timezone.now(),
        reverse=True,
    )

    context = {'patients': patients}
    return render(request, 'accounts/provider/providers_patients.html', context)


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
    total_earnings = completed_deliveries.aggregate(total=Sum('job__offered_pay'))['total'] or 0

    context = {
        'courier_profile': courier_profile,
        'available_jobs': available_jobs,
        'my_bids': my_bids,
        'active_deliveries': active_deliveries,
        'completed_deliveries': completed_deliveries,
        'total_completed': completed_deliveries.count(),
        'total_earnings': total_earnings,
    }
    return render(request, 'accounts/courier/courier_dashboard.html', context)
