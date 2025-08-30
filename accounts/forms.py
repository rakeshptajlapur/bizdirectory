# accounts/forms_allauth.py
from allauth.account.forms import SignupForm, ResetPasswordForm
from django import forms
from .models import Profile
from django.contrib.auth.models import User

class AllauthSignupForm(SignupForm):
    name = forms.CharField(max_length=30, required=True,
                         widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    # Remove username field from the form
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'username' in self.fields:
            del self.fields['username']  # Remove username field
    
    def save(self, request):
        # Generate username from email
        email = self.cleaned_data['email']
        username = email.split('@')[0]
        # Add numeric suffix if username exists
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        # Add username back to cleaned_data
        self.cleaned_data['username'] = username
        
        # Create the user with parent's save method
        user = super().save(request)
        
        # Save the name as first_name
        user.first_name = self.cleaned_data['name']
        user.save()
        
        # Create profile
        Profile.objects.get_or_create(user=user, defaults={'user_type': 'regular'})
        
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
        if self.instance and hasattr(self.instance, 'user'):
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        profile.user.first_name = self.cleaned_data['first_name']
        profile.user.last_name = self.cleaned_data['last_name']
        profile.user.email = self.cleaned_data['email']
        
        if commit:
            profile.user.save()
            profile.save()
        
        return profile

