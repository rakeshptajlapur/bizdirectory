from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

@login_required
def profile(request):
    """View and update user profile information"""
    
    # Ensure user has a profile
    if not hasattr(request.user, 'profile'):
        from .models import Profile
        Profile.objects.get_or_create(user=request.user, defaults={'user_type': 'regular'})
    
    try:
        from .forms_allauth import ProfileUpdateForm
    except ImportError as e:
        messages.error(request, "Profile form not available. Please contact support.")
        return redirect('directory:dashboard_home')
    
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user.profile)
        if form.is_valid():
            form.save()
            from .signals import send_profile_updated_email
            send_profile_updated_email.delay(request.user.id)
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('accounts:profile')
    else:
        form = ProfileUpdateForm(instance=request.user.profile)
    
    context = {
        'form': form,
        'active_tab': 'profile',
        'user': request.user,  # Ensure user is in context
    }
    
    return render(request, 'account/profile.html', context)

@login_required
def upgrade_to_business(request):
    """Upgrade regular user to business owner"""
    if request.user.profile.is_business_owner:
        messages.info(request, 'You are already a business owner.')
        return redirect('directory:dashboard_home')
    
    if request.method == 'POST':
        # Update user profile to business owner
        profile = request.user.profile
        profile.user_type = 'business_owner'
        profile.save()
        
        messages.success(request, 'Congratulations! Your account has been upgraded to business owner. You can now add business listings.')
        return redirect('directory:dashboard_home')
    
    context = {
        'active_tab': 'upgrade',
    }
    return render(request, 'account/upgrade_to_business.html', context)

@login_required
def password_change_redirect(request):
    """Redirect to allauth password change"""
    return redirect('account_change_password')