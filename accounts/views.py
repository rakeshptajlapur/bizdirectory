from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import PasswordChangeForm  # Add this import
from .forms import ProfileUpdateForm, CustomUserCreationForm  # Add CustomUserCreationForm
from directory.models import Business
from django.contrib.auth.models import User
from .signals import send_password_changed_email, send_profile_updated_email
from .signals import send_verification_email, send_welcome_email
from .models import EmailVerification
from django.utils import timezone
from datetime import timedelta

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    
    def form_valid(self, form):
        user = form.get_user()
        
        # Check if user is active
        if not user.is_active:
            messages.error(self.request, 'Please verify your email before logging in.')
            return redirect('accounts:verify_email')
        
        # Login the user
        login(self.request, user)
        messages.success(self.request, f'Welcome back, {user.first_name or user.username}!')
        
        return super().form_valid(form)
    
    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse('directory:home')

def register(request):
    """User registration with email verification"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Store email in session for verification
            request.session['pending_verification_email'] = user.email
            
            messages.success(request, 'Account created! Please check your email for verification code.')
            return redirect('accounts:verify_email')
        else:
            # Show specific form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/register.html', {'form': form})

# Add the missing login_view function
def login_view(request):
    """Use the class-based view for login"""
    return CustomLoginView.as_view()(request)

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('directory:home')

@login_required
def profile(request):
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
    
    context = {
        'form': form,
        'active_tab': 'profile',  # Add this
    }
    return render(request, 'accounts/profile.html', context)

class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:password_change_done')

    def form_valid(self, form):
        response = super().form_valid(form)
        # Queue password change notification
        send_password_changed_email.delay(self.request.user.id)
        return response

@login_required
def password_change(request):
    """Change password view"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Your password has been updated successfully.')
            return redirect('accounts:password_change_done')
    else:
        form = PasswordChangeForm(request.user)
    
    context = {
        'form': form,
        'active_tab': 'security',  # Add this
    }
    return render(request, 'accounts/password_change.html', context)

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
        'active_tab': 'upgrade',  # Add this
    }
    return render(request, 'accounts/upgrade_to_business.html', context)

def verify_email(request):
    """Email verification page"""
    if request.method == 'POST':
        otp_entered = request.POST.get('otp', '').strip()
        email = request.session.get('pending_verification_email')
        
        if not email:
            messages.error(request, 'Verification session expired. Please register again.')
            return redirect('accounts:register')
        
        try:
            user = User.objects.filter(email=email, is_active=False).first()
            
            if not user:
                messages.error(request, 'User not found or already verified.')
                return redirect('accounts:login')
                
            if not hasattr(user, 'email_verification'):
                messages.error(request, 'No verification record found.')
                return redirect('accounts:register')
                
            verification = user.email_verification
            
            if verification.otp_code == otp_entered and verification.is_otp_valid():
                # SUCCESS: Activate user
                user.is_active = True
                user.save()
                
                verification.is_verified = True
                verification.save()
                
                # Clear session
                if 'pending_verification_email' in request.session:
                    del request.session['pending_verification_email']
                
                # Login user immediately
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)
                
                # Send welcome email
                from .signals import send_welcome_email
                send_welcome_email.delay(user.id)
                
                messages.success(request, f'Welcome to FindNearBiz, {user.first_name}!')
                
                # Redirect based on user type
                if user.profile.user_type == 'business_owner':
                    return redirect('directory:subscription_plans')
                else:
                    return redirect('directory:home')
            else:
                if not verification.is_otp_valid():
                    messages.error(request, 'Verification code has expired.')
                else:
                    messages.error(request, 'Invalid verification code.')
                    
        except Exception as e:
            messages.error(request, 'Verification failed. Please try again.')
    
    # GET request - show verification form
    email = request.session.get('pending_verification_email')
    if not email:
        messages.error(request, 'No pending verification.')
        return redirect('accounts:register')
    
    try:
        user = User.objects.get(email=email, is_active=False)
        verification = user.email_verification
        remaining_time = max(0, int((verification.expires_at - timezone.now()).total_seconds()))
        
        return render(request, 'accounts/verify_email.html', {
            'email': email,
            'remaining_time': remaining_time,
        })
    except:
        messages.error(request, 'Verification session invalid.')
        return redirect('accounts:register')

def resend_otp(request):
    """Resend OTP verification code"""
    email = request.session.get('pending_verification_email')
    
    if not email:
        messages.error(request, 'No pending verification found.')
        return redirect('accounts:register')
    
    try:
        user = User.objects.get(email=email, is_active=False)
        verification = user.email_verification
        
        # Generate new OTP
        verification.otp_code = EmailVerification.generate_otp()
        verification.created_at = timezone.now()
        verification.expires_at = timezone.now() + timedelta(minutes=10)
        verification.save()
        
        # Send new OTP email
        send_verification_email.delay(user.id, verification.otp_code)
        
        messages.success(request, 'New verification code sent to your email.')
        
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('accounts:register')
    
    return redirect('accounts:verify_email')
