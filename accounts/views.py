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
from .signals import send_verification_email, send_welcome_email
from .models import EmailVerification
from django.utils import timezone
from datetime import timedelta

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.is_active = False  # Keep inactive until verified
                user.save()
                
                # Generate OTP and send email
                otp_code = EmailVerification.generate_otp()
                EmailVerification.objects.create(
                    user=user,
                    otp_code=otp_code
                )
                
                # Send verification email - wrap in try/except
                try:
                    send_verification_email.delay(user.id, otp_code)
                except Exception as e:
                    # Log the error but continue - don't break registration
                    print(f"Error sending verification email: {str(e)}")
                
                # Store email for verification
                request.session['pending_verification_email'] = user.email
                
                messages.success(request, 'Registration successful! Please check your email for verification code.')
                return redirect('accounts:verify_email')
            except Exception as e:
                # Log the error and show user-friendly message
                print(f"Registration error: {str(e)}")
                messages.error(request, 'Registration failed. Please try again.')
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
            user = User.objects.get(email=email, is_active=False)
            verification = user.email_verification
            
            if verification.otp_code == otp_entered and verification.is_otp_valid():
                # Activate user
                user.is_active = True
                user.save()
                
                # Mark as verified
                verification.is_verified = True
                verification.save()
                
                # Auto-login user
                login(request, user)
                
                # Send welcome email
                send_welcome_email.delay(user.id)
                
                # Clear session
                del request.session['pending_verification_email']
                
                messages.success(request, 'Email verified successfully! Welcome to BizDirectory.')
                
                # Redirect based on user type
                if user.profile.user_type == 'business_owner':
                    return redirect('directory:dashboard_home')
                else:
                    return redirect('directory:home')
            else:
                messages.error(request, 'Invalid or expired verification code. Please try again.')
                
        except User.DoesNotExist:
            messages.error(request, 'Verification failed. Please register again.')
            return redirect('accounts:register')
        except EmailVerification.DoesNotExist:
            messages.error(request, 'No verification code found. Please register again.')
            return redirect('accounts:register')
    
    return render(request, 'accounts/verify_email.html')

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
