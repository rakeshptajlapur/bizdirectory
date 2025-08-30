# accounts/forms_allauth.py
from allauth.account.forms import SignupForm, ResetPasswordForm
from django import forms
from .models import Profile
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

class AllauthSignupForm(SignupForm):
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    def save(self, request):
        user = super().save(request)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.is_active = False  # Keep users inactive until verified
        user.save()
        
        # Create profile as regular user
        Profile.objects.get_or_create(user=user, defaults={'user_type': 'regular'})
        
        return user

class AllauthPasswordResetForm(ResetPasswordForm):
    """Custom allauth password reset form using Celery"""
    
    def save(self, request, **kwargs):
        email = self.cleaned_data['email']
        
        try:
            # Find active user
            user = User.objects.get(email=email, is_active=True)
            
            # Generate reset URL using allauth's built-in method
            from allauth.account.utils import user_pk_to_url_str
            from allauth.account.forms import default_token_generator
            
            uid = user_pk_to_url_str(user)
            token = default_token_generator.make_token(user)
            
            # Build reset URL
            protocol = 'https' if request.is_secure() else 'http'
            domain = request.get_host()
            reset_url = f"{protocol}://{domain}/accounts/password/reset/key/{uid}-{token}/"
            
            # Send via Celery task
            from .signals import send_password_reset_email
            send_password_reset_email.delay(user.id, reset_url)
            
        except User.DoesNotExist:
            pass
        except Exception as e:
            print(f"Password reset error: {str(e)}")
            pass

class ProfileUpdateForm(forms.ModelForm):
    """Profile update form for allauth system"""
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

