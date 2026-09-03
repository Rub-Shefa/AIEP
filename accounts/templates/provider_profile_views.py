from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def provider_dashboard_view(request):
    return render(request, 'accounts/provider_dashboard.html')

@login_required
def provider_profile_view(request):
    return render(request, 'accounts/provider_profile.html')