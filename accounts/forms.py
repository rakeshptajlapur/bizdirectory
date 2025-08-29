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
    last_name = forms.CharField(max_length=30, required=False)
    user_type = forms.ChoiceField(
        choices=Profile.USER_TYPE_CHOICES,
        widget=forms.RadioSelect,
        required=True,
        initial='regular'
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add CSS classes
        for field_name, field in self.fields.items():
            if field_name != 'user_type':
                field.widget.attrs.update({'class': 'form-control'})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.is_active = False  # CRITICAL: INACTIVE until verified
        
        if commit:
            user.save()
            
            # Create profile
            from .models import Profile
            profile, created = Profile.objects.get_or_create(user=user)
            profile.user_type = self.cleaned_data['user_type']
            profile.save()
            
            # Create email verification
            from .models import EmailVerification
            from django.utils import timezone
            from datetime import timedelta
            
            EmailVerification.objects.filter(user=user).delete()
            
            verification = EmailVerification.objects.create(
                user=user,
                otp_code=EmailVerification.generate_otp(),
                expires_at=timezone.now() + timedelta(minutes=30)
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
    """Custom password reset form that uses our Celery task"""
    
    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        """Send password reset email via Celery"""
        user_email = context.get('email', to_email)
        
        try:
            # Only send to ACTIVE users
            user = User.objects.get(email=user_email, is_active=True)
            
            # Build reset URL
            protocol = context.get('protocol', 'https')
            domain = context.get('domain', 'findnearbiz.com')
            uid = context.get('uid', '')
            token = context.get('token', '')
            
            reset_url = f"{protocol}://{domain}/accounts/reset/{uid}/{token}/"
            
            # Send email via Celery
            from .signals import send_password_reset_email
            send_password_reset_email.delay(user.id, reset_url)
            
        except User.DoesNotExist:
            # Silent fail for security (don't reveal if email exists)
            pass
        except Exception as e:
            # Log error but don't crash
            pass

