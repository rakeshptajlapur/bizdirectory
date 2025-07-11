from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from .forms import UserRegisterForm, ProfileUpdateForm
from directory.models import Business
from django.contrib.auth.models import User
from .signals import send_password_changed_email, send_profile_updated_email

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        print(f"Form valid: {form.is_valid()}")
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Welcome to BizDirectory, {username}! Your account has been created.')
            
            # Automatically log in the user
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            
            # Redirect based on user type
            if user.profile.is_business_owner:
                return redirect('directory:dashboard_home')
            else:
                return redirect('directory:home')
        else:
            print(f"Form errors: {form.errors}")
    else:
        form = UserRegisterForm()
    
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Try to authenticate with username
        user = authenticate(request, username=username, password=password)
        
        # If authentication fails, try with email
        if user is None:
            try:
                user_obj = User.objects.get(email=username)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass
                
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            
            # Get the next parameter or redirect based on user type
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            elif hasattr(user, 'profile') and user.profile.is_business_owner:
                return redirect('directory:dashboard_home')
            else:
                return redirect('directory:home')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'accounts/login.html')

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('directory:home')

@login_required
def profile_view(request):
    """View and update user profile information"""
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user.profile)
        if form.is_valid():
            form.save()
            # Send profile update confirmation email via Celery
            send_profile_updated_email.delay(request.user.id)
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('accounts:profile')
    else:
        form = ProfileUpdateForm(instance=request.user.profile)
    
    return render(request, 'accounts/profile.html', {'form': form})

class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:password_change_done')

    def form_valid(self, form):
        response = super().form_valid(form)
        # Queue password change notification
        send_password_changed_email.delay(self.request.user.id)
        return response

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
    
    return render(request, 'accounts/upgrade_to_business.html')
