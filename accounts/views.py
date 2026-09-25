from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum, Count, Max, Q
from django.core.validators import validate_email
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
from django.views.decorators.http import require_POST
from datetime import datetime, timedelta
from decimal import Decimal
import mimetypes
import base64
from binascii import Error as BinasciiError
from django.core.files.base import ContentFile
from .forms import CustomUserCreationForm, CustomerAccountForm, CustomerProfileForm, CustomerSettingsAccountForm
from accounts.models import ProviderProfile, CustomerProfile, CourierProfile, SellerProfile
from catalog.models import Category, Product, Appointment, ProviderAvailabilitySlot
from messaging.models import Conversation, ChatMessage
from orders.models import Order, OrderItem, DeliveryJobPosting, DeliveryBid, Delivery
from orders.cart import Cart

APPOINTMENT_PLATFORM_FEE = Decimal('1.50')
APPOINTMENT_PAYMENT_METHODS = {
    'cash_visit': 'Pay at visit',
    'bkash': 'bKash wallet',
    'card': 'Visa/Mastercard',
    'bank': 'Bank transfer',
}

def home(request):
    categories = Category.objects.all()
    providers = ProviderProfile.objects.select_related('user').all()

    search_query = request.GET.get('q', '').strip()
    ai_search_used = False

    if search_query:
        providers = providers.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(specialty__icontains=search_query) |
            Q(degrees__icontains=search_query) |
            Q(bio__icontains=search_query) |
            Q(practice_locations__name__icontains=search_query) |
            Q(practice_locations__address__icontains=search_query)
        ).distinct()

        # Pass 1: exact/partial keyword match (fast, no AI call).
        products = Product.objects.filter(
            approval_status=Product.APPROVAL_APPROVED
        ).filter(
            Q(name__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(seller__store_name__icontains=search_query) |
            Q(seller__user__username__icontains=search_query)
        ).select_related('category', 'seller__user')

        # Pass 2: nothing matched by keyword -> ask the AI to reason about
        # the catalog semantically (e.g. "headache" -> "Paracetamol").
        if not products.exists():
            from ai_communication.ai_search import ai_semantic_product_search
            all_products = Product.objects.select_related('category', 'seller__user').filter(
                approval_status=Product.APPROVAL_APPROVED
            )
            products = ai_semantic_product_search(search_query, all_products)
            ai_search_used = bool(products)
    else:
        products = Product.objects.select_related('category', 'seller__user').filter(
            approval_status=Product.APPROVAL_APPROVED
        )

    for product in products:
        product.seller_display_name = product.seller.store_name or product.seller.user.get_full_name() or product.seller.user.username
    for provider in providers:
        provider.display_name = provider.user.get_full_name() or provider.user.username

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
    approved_products_count = Product.objects.filter(approval_status=Product.APPROVAL_APPROVED).count()
    pending_products_count = Product.objects.filter(approval_status=Product.APPROVAL_PENDING).count()
    rejected_products_count = Product.objects.filter(approval_status=Product.APPROVAL_REJECTED).count()
    pending_products = (
        Product.objects.filter(approval_status=Product.APPROVAL_PENDING)
        .select_related('seller__user', 'category')
        .order_by('-created_at')[:8]
    )
    low_stock_products = Product.objects.filter(
        approval_status=Product.APPROVAL_APPROVED,
        stock__lte=5,
    ).order_by('stock')[:6]
    low_stock_count = Product.objects.filter(
        approval_status=Product.APPROVAL_APPROVED,
        stock__lte=5,
    ).count()

    active_deliveries = Delivery.objects.exclude(status='Delivered').count()
    completed_deliveries = Delivery.objects.filter(status='Delivered').count()
    open_delivery_jobs = DeliveryJobPosting.objects.filter(is_active=True, delivery__isnull=True).count()

    ai_logs_total = AIQueryLog.objects.count()
    ai_fallback_count = AIQueryLog.objects.filter(fallback_triggered=True).count()
    ai_fallback_rate = round((ai_fallback_count / ai_logs_total) * 100, 1) if ai_logs_total else 0

    upcoming_appointments = Appointment.objects.filter(
        status='Scheduled', scheduled_time__gte=now
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
        'approved_products_count': approved_products_count,
        'pending_products_count': pending_products_count,
        'rejected_products_count': rejected_products_count,
        'pending_products': pending_products,
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
@user_passes_test(is_admin)
@require_POST
def admin_product_approval_view(request, product_id, action):
    product = get_object_or_404(Product, id=product_id)

    if action == 'approve':
        product.approval_status = Product.APPROVAL_APPROVED
        product.save(update_fields=['approval_status', 'is_approved', 'updated_at'])
        messages.success(request, f'"{product.name}" has been approved for the storefront.')
    elif action == 'reject':
        product.approval_status = Product.APPROVAL_REJECTED
        product.save(update_fields=['approval_status', 'is_approved', 'updated_at'])
        messages.warning(request, f'"{product.name}" has been rejected and hidden from customers.')
    else:
        messages.error(request, "That product approval action is not available.")

    return redirect(f"{reverse('admin_dashboard')}#products")

@login_required
def customer_dashboard_view(request):
    customer_profile, _ = CustomerProfile.objects.get_or_create(user=request.user)

    categories = Category.objects.all()
    products = Product.objects.select_related('category', 'seller__user').filter(
        approval_status=Product.APPROVAL_APPROVED
    ).order_by('-created_at')

    selected_category = request.GET.get('category', '')
    query = request.GET.get('q', '').strip()

    if selected_category:
        products = products.filter(category_id=selected_category)
    if query:
        products = products.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(category__name__icontains=query)
            | Q(seller__store_name__icontains=query)
            | Q(seller__user__username__icontains=query)
        )
    for product in products:
        product.seller_display_name = product.seller.store_name or product.seller.user.get_full_name() or product.seller.user.username

    # Browse Doctors â€” pulled straight from ProviderProfile, filterable by
    # specialty and free-text search, nothing hardcoded.
    doctors = (
        ProviderProfile.objects.select_related('user')
        .prefetch_related('practice_locations', 'availability_slots__location')
        .all()
        .order_by('-experience_years')
    )
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
    combined_doctor_query = doctor_query or query
    if combined_doctor_query:
        doctors = doctors.filter(
            Q(user__first_name__icontains=combined_doctor_query)
            | Q(user__last_name__icontains=combined_doctor_query)
            | Q(specialty__icontains=combined_doctor_query)
            | Q(user__username__icontains=combined_doctor_query)
            | Q(degrees__icontains=combined_doctor_query)
            | Q(bio__icontains=combined_doctor_query)
            | Q(practice_locations__name__icontains=combined_doctor_query)
            | Q(practice_locations__address__icontains=combined_doctor_query)
        )
    doctors = doctors.distinct()

    for doctor in doctors:
        doctor.display_name = doctor.user.get_full_name() or doctor.user.username
        doctor.booking_slots = [
            slot for slot in doctor.availability_slots.all()
            if slot.is_active and slot.location and slot.location.is_active
        ]

    orders = (
        Order.objects.filter(customer=customer_profile)
        .prefetch_related('items__product')
        .order_by('-created_at')[:10]
    )

    # My Appointments â€” real bookings against the Appointment model, split
    # into what's still coming up vs. what's already happened or was cancelled.
    now = timezone.now()
    all_appointments = (
        Appointment.objects.filter(patient=customer_profile)
        .select_related('provider__user')
        .order_by('scheduled_time')
    )
    upcoming_appointments = all_appointments.filter(status='Scheduled', scheduled_time__gte=now)
    past_appointments = (
        all_appointments.exclude(status='Scheduled', scheduled_time__gte=now)
        .order_by('-scheduled_time')[:10]
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
def doctor_detail_view(request, provider_id):
    provider = get_object_or_404(
        ProviderProfile.objects.select_related('user').prefetch_related(
            'practice_locations', 'availability_slots__location'
        ),
        id=provider_id,
    )
    provider.booking_slots = [
        slot for slot in provider.availability_slots.all()
        if slot.is_active and slot.location and slot.location.is_active
    ]
    provider.display_name = provider.user.get_full_name() or provider.user.username
    return render(request, 'accounts/customer/doctor_detail.html', {
        'provider': provider,
        'today_str': timezone.localdate().isoformat(),
    })


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
    """Two-step customer booking: review first, then confirm and save."""
    if request.method != 'POST':
        return redirect('customer_dashboard')

    customer_profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
    provider = get_object_or_404(ProviderProfile, id=provider_id)
    doctor_name = provider.user.get_full_name() or provider.user.username
    redirect_target = f"{reverse('doctor_detail', args=[provider.id])}#book-appointment"

    date_str = request.POST.get('appointment_date', '').strip()
    slot_id = request.POST.get('slot_id', '').strip()
    reason = request.POST.get('reason_for_visit', '').strip()

    if not date_str or not slot_id:
        messages.error(request, "Please choose both a date and an available appointment slot.")
        return redirect(redirect_target)

    slot = get_object_or_404(
        ProviderAvailabilitySlot.objects.select_related('location'),
        id=slot_id,
        provider=provider,
        is_active=True,
        location__is_active=True,
    )

    try:
        requested_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        naive_dt = datetime.combine(requested_date, slot.start_time)
    except ValueError:
        messages.error(request, "That date or time didn't look right. Please try again.")
        return redirect(redirect_target)

    appointment_dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())

    if appointment_dt < timezone.now():
        messages.error(request, "You can't book an appointment in the past.")
        return redirect(redirect_target)

    if appointment_dt.weekday() != slot.weekday:
        messages.error(request, f"That slot is only available on {slot.get_weekday_display()}.")
        return redirect(redirect_target)

    booked_count = Appointment.objects.filter(
        provider=provider,
        slot=slot,
        scheduled_time=appointment_dt,
        status='Scheduled',
    ).count()
    if booked_count >= slot.max_patients:
        messages.error(
            request,
            f"Dr. {doctor_name}'s {slot.location.name} slot is full for that date. Please choose another slot."
        )
        return redirect(redirect_target)

    latest_serial = Appointment.objects.filter(
        provider=provider,
        slot=slot,
        scheduled_time=appointment_dt,
    ).aggregate(max_serial=Max('serial_number'))['max_serial'] or 0
    serial_number = latest_serial + 1
    visit_fee = provider.consultation_fee
    platform_fee = APPOINTMENT_PLATFORM_FEE
    total_due = visit_fee + platform_fee
    appointment_mode = 'online' if slot.location.location_type == 'online' else 'offline'

    if request.POST.get('confirm_booking') != '1':
        return render(request, 'accounts/customer/appointment_confirm.html', {
            'provider': provider,
            'doctor_name': doctor_name,
            'customer_profile': customer_profile,
            'slot': slot,
            'appointment_dt': appointment_dt,
            'appointment_date': date_str,
            'reason': reason,
            'serial_number': serial_number,
            'appointment_mode': appointment_mode,
            'visit_fee': visit_fee,
            'platform_fee': platform_fee,
            'total_due': total_due,
            'payment_methods': APPOINTMENT_PAYMENT_METHODS.items(),
        })

    contact_email = request.POST.get('contact_email', '').strip()
    contact_phone = request.POST.get('contact_phone', '').strip()
    payment_method = request.POST.get('payment_method', 'cash_visit')
    payment_phone = request.POST.get('payment_phone', '').strip()

    if not contact_email:
        messages.error(request, "Please enter an email address for appointment confirmation.")
        return redirect(redirect_target)
    try:
        validate_email(contact_email)
    except ValidationError:
        messages.error(request, "Please enter a valid email address for appointment confirmation.")
        return redirect(redirect_target)
    if not contact_phone:
        messages.error(request, "Please enter a phone number for appointment confirmation.")
        return redirect(redirect_target)
    if payment_method not in APPOINTMENT_PAYMENT_METHODS:
        messages.error(request, "Please choose a valid payment method.")
        return redirect(redirect_target)
    if payment_method == 'bkash' and not payment_phone:
        messages.error(request, "Please enter the bKash wallet number for this simulated payment.")
        return redirect(redirect_target)

    with transaction.atomic():
        locked_slot = get_object_or_404(
            ProviderAvailabilitySlot.objects.select_for_update().select_related('location'),
            id=slot.id,
            provider=provider,
            is_active=True,
            location__is_active=True,
        )
        booked_count = Appointment.objects.filter(
            provider=provider,
            slot=locked_slot,
            scheduled_time=appointment_dt,
            status='Scheduled',
        ).count()
        if booked_count >= locked_slot.max_patients:
            messages.error(
                request,
                f"Dr. {doctor_name}'s {locked_slot.location.name} slot is full for that date. Please choose another slot."
            )
            return redirect(redirect_target)

        latest_serial = Appointment.objects.filter(
            provider=provider,
            slot=locked_slot,
            scheduled_time=appointment_dt,
        ).aggregate(max_serial=Max('serial_number'))['max_serial'] or 0
        serial_number = latest_serial + 1
        Appointment.objects.create(
            patient=customer_profile,
            provider=provider,
            location=locked_slot.location,
            slot=locked_slot,
            appointment_mode=appointment_mode,
            appointment_place_name=locked_slot.location.name,
            appointment_place_address=locked_slot.location.address,
            serial_number=serial_number,
            contact_email=contact_email,
            contact_phone=contact_phone,
            visit_fee=visit_fee,
            platform_fee=platform_fee,
            total_due=total_due,
            payment_method=payment_method,
            payment_phone=payment_phone,
            payment_status='Pending',
            scheduled_time=appointment_dt,
            notes=reason,
            status='Scheduled',
        )
    messages.success(
        request,
        f"Appointment booked with Dr. {doctor_name}. Serial #{serial_number} at {slot.location.name} on {appointment_dt.strftime('%b %d, %Y at %I:%M %p')}."
    )
    return redirect(f"{reverse('customer_dashboard')}#appointments")

@login_required
def cancel_appointment_view(request, appointment_id):
    """Lets a customer cancel their own upcoming appointment."""
    if request.method != 'POST':
        return redirect('customer_dashboard')

    customer_profile = getattr(request.user, 'customer_profile', None)
    appointment = get_object_or_404(Appointment, id=appointment_id, patient=customer_profile)

    if appointment.status == 'Scheduled':
        appointment.status = 'Cancelled'
        appointment.save(update_fields=['status'])
        messages.success(request, "Your appointment has been cancelled.")
    else:
        messages.error(request, "This appointment can no longer be cancelled.")

    return redirect(f"{reverse('customer_dashboard')}#appointments")


def _conversation_partner(conversation, user):
    return conversation.participant2 if conversation.participant1_id == user.id else conversation.participant1


def _chat_attachment_type(uploaded_file):
    if not uploaded_file:
        return ''
    guessed_type = uploaded_file.content_type or mimetypes.guess_type(uploaded_file.name)[0] or ''
    if guessed_type.startswith('image/'):
        return 'image'
    if guessed_type.startswith('video/'):
        return 'video'
    return ''


def _visible_conversation_messages(conversation, user):
    return list(
        conversation.messages
        .exclude(deleted_for_users=user)
        .select_related('sender')
        .order_by('timestamp')
    )


@login_required
def customer_messages_view(request):
    customer_profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
    selected_conversation = None

    provider_id = request.GET.get('provider_id')
    seller_id = request.GET.get('seller_id')
    conversation_id = request.GET.get('conversation_id')

    if provider_id:
        provider = get_object_or_404(ProviderProfile.objects.select_related('user'), id=provider_id)
        if provider.user_id != request.user.id:
            selected_conversation = Conversation.get_or_create_between(
                request.user,
                provider.user,
                thread_type='Customer-Provider',
            )
            selected_conversation.deleted_for_users.remove(request.user)
    elif seller_id:
        seller = get_object_or_404(SellerProfile.objects.select_related('user'), id=seller_id)
        if seller.user_id != request.user.id:
            selected_conversation = Conversation.get_or_create_between(
                request.user,
                seller.user,
                thread_type='Customer-Seller',
            )
            selected_conversation.deleted_for_users.remove(request.user)
    elif conversation_id:
        selected_conversation = get_object_or_404(
            Conversation,
            Q(participant1=request.user) | Q(participant2=request.user),
            id=conversation_id,
            thread_type__in=['Customer-Seller', 'Customer-Provider'],
        )
        if selected_conversation.deleted_for_users.filter(id=request.user.id).exists():
            messages.error(request, "That conversation was deleted from your inbox.")
            return redirect('customer_messages')

    if request.method == 'POST':
        selected_conversation = get_object_or_404(
            Conversation,
            Q(participant1=request.user) | Q(participant2=request.user),
            id=request.POST.get('conversation_id'),
            thread_type__in=['Customer-Seller', 'Customer-Provider'],
        )
        action = request.POST.get('action', 'send')

        if action == 'delete_conversation':
            selected_conversation.deleted_for_users.add(request.user)
            messages.success(request, "Conversation deleted from your inbox.")
            return redirect('customer_messages')

        if action == 'delete_message':
            chat_message = get_object_or_404(
                ChatMessage,
                id=request.POST.get('message_id'),
                conversation=selected_conversation,
            )
            chat_message.deleted_for_users.add(request.user)
            messages.success(request, "Message deleted for you.")
            return redirect(f"{reverse('customer_messages')}?conversation_id={selected_conversation.id}")

        body = request.POST.get('message', '').strip()
        attachment = request.FILES.get('attachment')
        attachment_type = _chat_attachment_type(attachment)

        provider_profile = getattr(_conversation_partner(selected_conversation, request.user), 'provider_profile', None)
        online_appointment = provider_profile and Appointment.objects.filter(
            patient=customer_profile,
            provider=provider_profile,
            appointment_mode='online',
        ).exists()
        if attachment and not online_appointment:
            messages.error(request, "Photos and videos are available only for an online doctor appointment.")
            return redirect(f"{reverse('customer_messages')}?conversation_id={selected_conversation.id}")
        if attachment and not attachment_type:
            messages.error(request, "Please attach an image or a short video file.")
            return redirect(f"{reverse('customer_messages')}?conversation_id={selected_conversation.id}")
        if attachment and attachment.size > 20 * 1024 * 1024:
            messages.error(request, "Please keep chat attachments under 20 MB.")
            return redirect(f"{reverse('customer_messages')}?conversation_id={selected_conversation.id}")
        if not body and not attachment:
            messages.error(request, "Write a message or attach a file before sending.")
            return redirect(f"{reverse('customer_messages')}?conversation_id={selected_conversation.id}")

        ChatMessage.objects.create(
            conversation=selected_conversation,
            sender=request.user,
            content=body,
            attachment=attachment,
            attachment_type=attachment_type,
        )
        selected_conversation.deleted_for_users.remove(request.user)
        return redirect(f"{reverse('customer_messages')}?conversation_id={selected_conversation.id}")

    conversations = list(
        Conversation.objects.filter(
            Q(participant1=request.user) | Q(participant2=request.user),
            thread_type__in=['Customer-Seller', 'Customer-Provider'],
        )
        .exclude(deleted_for_users=request.user)
        .annotate(last_message_at=Max('messages__timestamp'))
        .select_related('participant1', 'participant2')
        .prefetch_related('messages')
        .order_by('-created_at')
    )

    visible_conversations = []
    for conversation in conversations:
        visible_messages = _visible_conversation_messages(conversation, request.user)
        if not visible_messages:
            continue
        conversation.other_user = _conversation_partner(conversation, request.user)
        conversation.last_message = visible_messages[-1]
        conversation.message_count = len(visible_messages)
        visible_conversations.append(conversation)

    conversations = visible_conversations
    conversations.sort(
        key=lambda conversation: (
            conversation.last_message.timestamp if conversation.last_message else conversation.created_at,
            conversation.message_count,
        ),
        reverse=True,
    )
    if selected_conversation is None and conversations:
        selected_conversation = conversations[0]

    chat_messages = []
    selected_partner = None
    allow_attachments = False
    if selected_conversation:
        selected_partner = _conversation_partner(selected_conversation, request.user)
        provider_profile = getattr(selected_partner, 'provider_profile', None)
        allow_attachments = bool(provider_profile and Appointment.objects.filter(
            patient=customer_profile,
            provider=provider_profile,
            appointment_mode='online',
        ).exists())
        chat_messages = _visible_conversation_messages(selected_conversation, request.user)

    context = {
        'customer_profile': customer_profile,
        'conversations': conversations,
        'selected_conversation': selected_conversation,
        'selected_partner': selected_partner,
        'chat_messages': chat_messages,
        'allow_attachments': allow_attachments,
    }
    return render(request, 'accounts/customer/messages.html', context)


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

    # Order History filter - practical status filter so a seller with a long
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
            messages.success(request, f"Appointment with {appointment.patient.user.username} marked as {new_status}.")
        return redirect('provider_dashboard')

    now = timezone.now()

    appointments = (
        Appointment.objects.filter(provider=provider_profile)
        .select_related('patient__user')
        .order_by('scheduled_time')
    )

    upcoming_appointments = appointments.filter(status='Scheduled', scheduled_time__gte=now)
    past_due_appointments = appointments.filter(status='Scheduled', scheduled_time__lt=now)
    completed_appointments = appointments.filter(status='Completed').order_by('-scheduled_time')
    cancelled_appointments = appointments.filter(status='Cancelled').order_by('-scheduled_time')

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
        .select_related('patient__user')
        .order_by('-scheduled_time')
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

    conversations = list(
        Conversation.objects.filter(
            Q(participant1=request.user) | Q(participant2=request.user),
            thread_type='Customer-Provider',
        )
        .exclude(deleted_for_users=request.user)
        .annotate(last_message_at=Max('messages__timestamp'))
        .select_related('participant1', 'participant2')
        .prefetch_related('messages')
        .order_by('-created_at')
    )

    patients = []
    for conversation in conversations:
        visible_messages = _visible_conversation_messages(conversation, request.user)
        if not visible_messages:
            continue
        patient_user = _conversation_partner(conversation, request.user)
        patient_profile = getattr(patient_user, 'customer_profile', None)
        if patient_profile:
            patient_profile.conversation_id = conversation.id
            patient_profile.last_message = visible_messages[-1]
            patient_profile.message_count = len(visible_messages)
            patient_profile.sort_at = patient_profile.last_message.timestamp if patient_profile.last_message else conversation.created_at
            patients.append(patient_profile)
    patients.sort(
        key=lambda patient: (patient.sort_at, patient.message_count),
        reverse=True,
    )

    selected_patient_id = request.GET.get('patient_id')
    if not selected_patient_id and patients:
        selected_patient_id = str(patients[0].id)
    selected_patient = None
    chat_messages = []
    attachment_allowed = False

    if selected_patient_id:
        selected_patient = get_object_or_404(CustomerProfile, id=selected_patient_id)
        conversation = Conversation.objects.filter(
            Q(participant1=request.user, participant2=selected_patient.user)
            | Q(participant1=selected_patient.user, participant2=request.user),
            thread_type='Customer-Provider',
        ).first()
        if conversation is None:
            messages.error(request, "The patient needs to start the conversation first.")
            return redirect('provider_messages')
        if conversation.deleted_for_users.filter(id=request.user.id).exists():
            messages.error(request, "That conversation was deleted from your inbox.")
            return redirect('provider_messages')

        has_patient_message = conversation.messages.exclude(deleted_for_users=request.user).filter(sender=selected_patient.user).exists()
        if not has_patient_message:
            messages.error(request, "The patient needs to send the first message before you can reply.")
            return redirect('provider_messages')

        attachment_allowed = Appointment.objects.filter(
            patient=selected_patient,
            provider=provider_profile,
            appointment_mode='online',
        ).exists()

        if request.method == 'POST':
            action = request.POST.get('action', 'send')

            if action == 'delete_conversation':
                conversation.deleted_for_users.add(request.user)
                messages.success(request, "Conversation deleted from your inbox.")
                return redirect('provider_messages')

            if action == 'delete_message':
                chat_message = get_object_or_404(
                    ChatMessage,
                    id=request.POST.get('message_id'),
                    conversation=conversation,
                )
                chat_message.deleted_for_users.add(request.user)
                messages.success(request, "Message deleted for you.")
                return redirect(f"{request.path}?patient_id={selected_patient_id}")

            body = request.POST.get('message', '').strip()
            attachment = request.FILES.get('attachment')
            attachment_type = _chat_attachment_type(attachment)

            if attachment and not attachment_allowed:
                messages.error(request, "File sharing is only enabled for online appointment patients.")
                return redirect(f"{request.path}?patient_id={selected_patient_id}")
            if attachment and not attachment_type:
                messages.error(request, "Please attach an image or a short video file.")
                return redirect(f"{request.path}?patient_id={selected_patient_id}")
            if attachment and attachment.size > 20 * 1024 * 1024:
                messages.error(request, "Please keep chat attachments under 20 MB.")
                return redirect(f"{request.path}?patient_id={selected_patient_id}")
            if body or attachment:
                ChatMessage.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    content=body,
                    attachment=attachment,
                    attachment_type=attachment_type,
                )
                conversation.deleted_for_users.remove(request.user)
                return redirect(f"{request.path}?patient_id={selected_patient_id}")

        chat_messages = _visible_conversation_messages(conversation, request.user)

    context = {
        'patients': patients,
        'selected_patient': selected_patient,
        'chat_messages': chat_messages,
        'attachment_allowed': attachment_allowed,
    }
    return render(request, 'accounts/provider/provider_messages.html', context)


@login_required
def seller_messages_view(request):
    seller_profile = getattr(request.user, 'seller_profile', None)
    if seller_profile is None:
        messages.error(request, "You need a seller profile to access messages.")
        return redirect_based_on_role(request.user)

    conversations = list(
        Conversation.objects.filter(
            Q(participant1=request.user) | Q(participant2=request.user),
            thread_type='Customer-Seller',
        )
        .exclude(deleted_for_users=request.user)
        .annotate(last_message_at=Max('messages__timestamp'))
        .select_related('participant1', 'participant2')
        .prefetch_related('messages')
        .order_by('-created_at')
    )

    if request.method == 'POST':
        selected_conversation = get_object_or_404(
            Conversation,
            Q(participant1=request.user) | Q(participant2=request.user),
            id=request.POST.get('conversation_id'),
            thread_type='Customer-Seller',
        )
        action = request.POST.get('action', 'send')

        if action == 'delete_conversation':
            selected_conversation.deleted_for_users.add(request.user)
            messages.success(request, "Conversation deleted from your inbox.")
            return redirect('seller_messages')

        if action == 'delete_message':
            chat_message = get_object_or_404(
                ChatMessage,
                id=request.POST.get('message_id'),
                conversation=selected_conversation,
            )
            chat_message.deleted_for_users.add(request.user)
            messages.success(request, "Message deleted for you.")
            return redirect(f"{reverse('seller_messages')}?conversation_id={selected_conversation.id}")

        body = request.POST.get('message', '').strip()
        if body:
            ChatMessage.objects.create(
                conversation=selected_conversation,
                sender=request.user,
                content=body,
            )
            selected_conversation.deleted_for_users.remove(request.user)
        return redirect(f"{reverse('seller_messages')}?conversation_id={selected_conversation.id}")

    visible_conversations = []
    for conversation in conversations:
        visible_messages = _visible_conversation_messages(conversation, request.user)
        if not visible_messages:
            continue
        conversation.other_user = _conversation_partner(conversation, request.user)
        conversation.last_message = visible_messages[-1]
        conversation.message_count = len(visible_messages)
        visible_conversations.append(conversation)

    conversations = visible_conversations
    conversations.sort(
        key=lambda conversation: (
            conversation.last_message.timestamp if conversation.last_message else conversation.created_at,
            conversation.message_count,
        ),
        reverse=True,
    )

    selected_conversation = None
    conversation_id = request.GET.get('conversation_id')
    if conversation_id:
        selected_conversation = get_object_or_404(
            Conversation,
            Q(participant1=request.user) | Q(participant2=request.user),
            id=conversation_id,
            thread_type='Customer-Seller',
        )
        if selected_conversation.deleted_for_users.filter(id=request.user.id).exists():
            messages.error(request, "That conversation was deleted from your inbox.")
            return redirect('seller_messages')
    elif conversations:
        selected_conversation = conversations[0]

    selected_customer = None
    chat_messages = []
    if selected_conversation:
        selected_customer = _conversation_partner(selected_conversation, request.user)
        ChatMessage.objects.filter(
            conversation=selected_conversation,
            is_read=False,
        ).exclude(sender=request.user).update(is_read=True)
        chat_messages = _visible_conversation_messages(selected_conversation, request.user)

    return render(request, 'accounts/seller/messages.html', {
        'seller_profile': seller_profile,
        'conversations': conversations,
        'selected_conversation': selected_conversation,
        'selected_customer': selected_customer,
        'chat_messages': chat_messages,
    })

@login_required
def provider_patients_view(request):
    provider_profile = getattr(request.user, 'provider_profile', None)
    if provider_profile is None:
        messages.error(request, "You need a provider profile to access patient records.")
        return redirect_based_on_role(request.user)

    appointments = (
        Appointment.objects.filter(provider=provider_profile)
        .select_related('patient__user')
        .order_by('patient_id', '-scheduled_time')
    )

    # Group this provider's appointments by patient, newest visit first.
    patients_map = {}
    for appt in appointments:
        cust_id = appt.patient_id
        entry = patients_map.setdefault(cust_id, {
            'customer': appt.patient,
            'appointments': [],
            'total_visits': 0,
            'last_visit': None,
        })
        entry['appointments'].append(appt)
        entry['total_visits'] += 1
        if entry['last_visit'] is None or appt.scheduled_time > entry['last_visit']:
            entry['last_visit'] = appt.scheduled_time

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


