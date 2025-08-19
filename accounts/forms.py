from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm
from .models import Profile
from affiliate.models import AffiliateProfile  # Import from affiliate app instead
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


# No custom password reset form needed - we'll use Django's default
class CustomPasswordResetForm(PasswordResetForm):
    """
    Custom password reset form that uses our existing Celery task
    """
    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        """
        Override to use our Celery task instead of sending directly
        """
        # Get user from the context
        user_email = context.get('email', '')
        try:
            user = User.objects.get(email=user_email)
            # Extract token and uid from context for complete reset URL
            protocol = context.get('protocol', 'http')
            domain = context.get('domain', 'example.com')
            uid = context.get('uid', '')
            token = context.get('token', '')
            # Make sure the URL includes the complete path to the reset confirm view
            # Use the accounts:password_reset_confirm URL as defined in urls.py
            reset_url = f"{protocol}://{domain}/accounts/reset/{uid}/{token}/"
            
            # Debug logging
            print(f"DEBUG: Password reset URL: {reset_url}")
            print(f"DEBUG: User ID: {user.id}, Email: {user.email}")
            
            # Use our existing Celery task
            send_password_reset_email.delay(user.id, reset_url)
        except User.DoesNotExist:
            # If user doesn't exist, don't send email (same as Django default)
            pass

