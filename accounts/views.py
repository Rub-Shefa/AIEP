from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from .forms import CustomUserCreationForm
from accounts.models import ProviderProfile
from catalog.models import Category, Product

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
    elif hasattr(user, 'sellerprofile'):
        return redirect('seller_dashboard')
    elif hasattr(user, 'providerprofile'):
        return redirect('provider_dashboard')
    elif hasattr(user, 'courierprofile'):
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
    return render(request, 'accounts/admin_dashboard.html')

@login_required
def customer_dashboard_view(request):
    return render(request, 'accounts/customer_dashboard.html')

@login_required
def seller_dashboard_view(request):
    return render(request, 'accounts/seller_dashboard.html')

@login_required
def provider_dashboard_view(request):
    return render(request, 'accounts/provider_dashboard.html')

@login_required
def courier_dashboard_view(request):
    return render(request, 'accounts/courier_dashboard.html')