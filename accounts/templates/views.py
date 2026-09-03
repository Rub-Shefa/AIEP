from ai_communication.models import ChatMessage  # Adjust import path if model exists elsewhere

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
    return render(request, 'accounts/provider_appointments.html', context)


@login_required
def provider_messages_view(request):
    provider_profile = getattr(request.user, 'provider_profile', None)
    if provider_profile is None:
        messages.error(request, "You need a provider profile to access messages.")
        return redirect_based_on_role(request.user)

    # Fetch distinct patients who have booked appointments with this provider
    patients = (
        CustomerProfile.objects.filter(appointment__provider=provider_profile)
        .distinct()
        .select_related('user')
    )

    selected_patient_id = request.GET.get('patient_id')
    selected_patient = None
    chat_messages = []

    if selected_patient_id:
        selected_patient = get_object_or_404(CustomerProfile, id=selected_patient_id)
        if request.method == 'POST':
            body = request.POST.get('message', '').strip()
            if body:
                ChatMessage.objects.create(
                    sender=request.user,
                    recipient=selected_patient.user,
                    message=body
                )
                messages.success(request, "Message sent successfully.")
                return redirect(f"{request.path}?patient_id={selected_patient_id}")

        chat_messages = ChatMessage.objects.filter(
            (Q(sender=request.user) & Q(recipient=selected_patient.user)) |
            (Q(sender=selected_patient.user) & Q(recipient=request.user))
        ).order_by('timestamp')

    context = {
        'patients': patients,
        'selected_patient': selected_patient,
        'chat_messages': chat_messages,
    }
    return render(request, 'accounts/provider_messages.html', context)