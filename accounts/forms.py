from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm
from .models import Profile
from .signals import send_password_reset_email

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    user_type = forms.ChoiceField(choices=Profile.USER_TYPE_CHOICES)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            # Save user type to profile
            user_type = self.cleaned_data.get('user_type')
            if hasattr(user, 'profile'):
                user.profile.user_type = user_type
                user.profile.save()
        
        return user

# Add the missing CustomUserCreationForm
class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    user_type = forms.ChoiceField(
        choices=Profile.USER_TYPE_CHOICES,
        initial='regular',
        widget=forms.RadioSelect,
        help_text="Choose your account type"
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'user_type']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add CSS classes and placeholders
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Choose a username'
        })
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
        self.fields['first_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter your first name'
        })
        self.fields['last_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Enter your last name'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Create a strong password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        })
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.is_active = False  # User needs to verify email first
        
        if commit:
            user.save()
            
            # Create/update profile with user type
            profile, created = Profile.objects.get_or_create(user=user)
            profile.user_type = self.cleaned_data['user_type']
            profile.save()
            
            # Create email verification record
            from .models import EmailVerification
            from django.utils import timezone
            from datetime import timedelta
            
            verification, created = EmailVerification.objects.get_or_create(
                user=user,
                defaults={
                    'otp_code': EmailVerification.generate_otp(),
                    'expires_at': timezone.now() + timedelta(minutes=10)
                }
            )
            
            # Send verification email
            from .signals import send_verification_email
            send_verification_email.delay(user.id, verification.otp_code)
        
        return user

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['phone']
        
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate user fields
        if self.instance and hasattr(self.instance, 'user'):
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        # Update user fields
        profile.user.first_name = self.cleaned_data['first_name']
        profile.user.last_name = self.cleaned_data['last_name']
        profile.user.email = self.cleaned_data['email']
        
        if commit:
            profile.user.save()
            profile.save()
        
        return profile

class CustomPasswordResetForm(PasswordResetForm):
    """
    Custom password reset form that uses our existing Celery task
    """
    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        """
        Override to use our Celery task instead of sending directly
        """
        # Get user email from the context
        user_email = context.get('email', to_email)
        
        try:
            # Find user by email
            user = User.objects.get(email=user_email, is_active=True)
            
            # Extract token and uid from context for complete reset URL
            protocol = context.get('protocol', 'https')
            domain = context.get('domain', 'findnearbiz.com')
            uid = context.get('uid', '')
            token = context.get('token', '')
            
            # Create the complete reset URL
            reset_url = f"{protocol}://{domain}/accounts/reset/{uid}/{token}/"
            
            # Debug logging
            print(f"DEBUG: Password reset for {user.email}")
            print(f"DEBUG: Reset URL: {reset_url}")
            
            # Use our existing Celery task
            send_password_reset_email.delay(user.id, reset_url)
            
        except User.DoesNotExist:
            # If user doesn't exist, don't send email (same as Django default behavior)
            print(f"DEBUG: No active user found with email: {user_email}")
            pass
        except Exception as e:
            # Log the error but don't raise it (to prevent 503 errors)
            print(f"ERROR: Password reset failed for {user_email}: {str(e)}")
            pass

