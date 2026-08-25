from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import CustomerProfile


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm outline-none',
            'placeholder': 'name@example.com'
        })
    )

    class Meta:
        model = User
        fields = ('username', 'email')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm outline-none',
                'placeholder': 'johndoe'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        input_style = 'w-full px-4 py-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-sm outline-none'
        self.fields['password1'].widget.attrs.update({'class': input_style, 'placeholder': '••••••••'})
        self.fields['password2'].widget.attrs.update({'class': input_style, 'placeholder': '••••••••'})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            # Automatically create a default CustomerProfile for new signups
            CustomerProfile.objects.get_or_create(user=user)
        return user

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email")  # Only include User model fields here

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        input_class = "form-input"

        self.fields["username"].widget.attrs.update({
            "class": input_class,
            "placeholder": "Choose a username",
        })
        self.fields["email"].widget.attrs.update({
            "class": input_class,
            "placeholder": "you@organisation.com",
        })
        self.fields["password1"].widget.attrs.update({
            "class": input_class,
            "placeholder": "Create a secure password",
        })
        self.fields["password2"].widget.attrs.update({
            "class": input_class,
            "placeholder": "Repeat your password",
        })

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            CustomerProfile.objects.get_or_create(user=user)
        return user