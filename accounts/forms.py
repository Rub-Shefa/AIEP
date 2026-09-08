import re  # Fixes "re is not defined"
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError  
from django.core.validators import RegexValidator  
from . import models

ROLE_CHOICES = (
    ('customer', 'Customer / Patient'),
    ('seller', 'Medical Supplier / Pharmacy'),
    ('provider', 'Healthcare Provider / Doctor'),
    ('courier', 'Courier / Delivery Service'),
)

OCCUPATION_CHOICES = (
    ('student', 'Student'),
    ('housewife', 'Housewife'),
    ('employed', 'Employed Professional'),
    ('other', 'Other'),
)

phone_regex = RegexValidator(
    regex=r'^(?:\+8801|01)[3-9]\d{8}$',
    message="Enter a valid Bangladeshi phone number (e.g., 01712345678 or +8801712345678)."
)

INPUT_STYLE = 'w-full rounded-xl border border-slate-300 px-4 py-2.5 text-sm bg-white focus:ring-2 focus:ring-teal/30 focus:border-teal outline-none transition-all'

class CustomUserCreationForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        initial='customer',
        widget=forms.Select(attrs={'id': 'id_role', 'class': INPUT_STYLE})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': INPUT_STYLE, 'placeholder': 'name@example.com'})
    )
    phone_number = forms.CharField(
        validators=[phone_regex],
        required=True,
        widget=forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': '017XXXXXXXX'})
    )

    # Dynamic Profile Fields
    occupation = forms.ChoiceField(
        choices=[('student', 'Student'), ('housewife', 'Housewife'), ('employed', 'Employed'), ('other', 'Other')],
        required=False,
        widget=forms.Select(attrs={'class': INPUT_STYLE})
    )
    store_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': 'Store Name'}))
    company_description = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2, 'class': INPUT_STYLE}))
    offline_location = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': INPUT_STYLE}))
    specialty = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': INPUT_STYLE}))
    degrees = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': INPUT_STYLE}))
    vehicle_type = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': INPUT_STYLE}))

    class Meta:
        model = User
        fields = ('username', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': INPUT_STYLE, 'placeholder': 'johndoe'})
        self.fields['password1'].widget.attrs.update({'class': INPUT_STYLE, 'placeholder': '••••••••'})
        self.fields['password2'].widget.attrs.update({'class': INPUT_STYLE, 'placeholder': '••••••••'})

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip()
        # Remove extra spaces or dashes
        phone = re.sub(r'[\s\-]', '', phone)
        
        # Enforce exact length rules for local (11 digits) or international (+880 = 14 chars)
        if phone.startswith('01') and len(phone) != 11:
            raise ValidationError("Local mobile numbers must be exactly 11 digits.")
        elif phone.startswith('+8801') and len(phone) != 14:
            raise ValidationError("International format mobile numbers must be exactly 14 characters (+8801XXXXXXXXX).")
            
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            role = self.cleaned_data.get('role')
            phone = self.cleaned_data.get('phone_number')

            if role == 'customer' and hasattr(models, 'CustomerProfile'):
                models.CustomerProfile.objects.get_or_create(user=user, defaults={'phone_number': phone})
            elif role == 'seller' and hasattr(models, 'SellerProfile'):
                models.SellerProfile.objects.get_or_create(
                    user=user, 
                    defaults={'store_name': self.cleaned_data.get('store_name') or f"{user.username}'s Store"}
                )
            elif role == 'provider' and hasattr(models, 'ProviderProfile'):
                models.ProviderProfile.objects.get_or_create(
                    user=user, 
                    defaults={'specialty': self.cleaned_data.get('specialty') or 'General Practice'}
                )
            elif role == 'courier' and hasattr(models, 'CourierProfile'):
                models.CourierProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'vehicle_type': self.cleaned_data.get('vehicle_type') or 'Motorbike',
                        'service_zone': self.cleaned_data.get('offline_location') or '',
                    }
                )

        return user

class RegisterForm(CustomUserCreationForm):
    """Maintains backward compatibility across imports"""
    pass


class CustomerProfileForm(forms.ModelForm):
    class Meta:
        model = models.CustomerProfile
        fields = ('avatar_image', 'phone_number', 'occupation', 'location', 'health_preferences')
        widgets = {
            'avatar_image': forms.FileInput(attrs={'class': 'hidden', 'accept': 'image/png,image/jpeg,image/webp'}),
            'phone_number': forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': '017XXXXXXXX'}),
            'occupation': forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': 'Student, professional, etc.'}),
            'location': forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': 'City, country'}),
            'health_preferences': forms.Textarea(attrs={'class': INPUT_STYLE, 'rows': 4, 'placeholder': 'Optional preferences that help us personalize your experience'}),
        }


class CustomerAccountForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': 'Last name'}),
        }


class CustomerSettingsAccountForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'email')
        widgets = {
            'username': forms.TextInput(attrs={'class': INPUT_STYLE, 'placeholder': 'username'}),
            'email': forms.EmailInput(attrs={'class': INPUT_STYLE, 'placeholder': 'name@example.com'}),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        qs = User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("That username is already taken.")
        return username
