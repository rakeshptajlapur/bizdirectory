from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from .forms import ProfileUpdateForm

@login_required
def profile(request):
    """View and update user profile information"""
    
    # Ensure user has a profile
    if not hasattr(request.user, 'profile'):
        from .models import Profile
        Profile.objects.get_or_create(user=request.user, defaults={'user_type': 'regular'})
    
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('accounts:profile')
    else:
        form = ProfileUpdateForm(instance=request.user.profile)
    
    context = {
        'form': form,
        'active_tab': 'profile',
        'user': request.user,
    }
    return render(request, 'account/profile.html', context)

@login_required
def upgrade_to_business(request):
    """Upgrade regular user to business owner"""
    if request.user.profile.is_business_owner:
        messages.info(request, 'You are already a business owner.')
        return redirect('directory:dashboard_home')
    
    if request.method == 'POST':
        profile = request.user.profile
        profile.user_type = 'business_owner'
        profile.save()
        
        messages.success(request, 'Congratulations! Your account has been upgraded to business owner.')
        return redirect('directory:dashboard_home')
    
    context = {
        'active_tab': 'upgrade',
    }
    return render(request, 'account/upgrade_to_business.html', context)

@login_required
def password_change_redirect(request):
    """Redirect to allauth password change"""
    return redirect('account_change_password')

@login_required
def post_login_redirect(request):
    """
    Handle post-login redirect based on user verification status
    """
    user = request.user
    
    # Check if user is verified (either through email or social auth)
    if user.is_active:
        # User is verified, go to dashboard
        return redirect('directory:dashboard_home')
    else:
        # User needs email verification
        return redirect('account_email')