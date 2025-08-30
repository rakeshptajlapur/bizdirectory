# accounts/forms_allauth.py
from allauth.account.forms import SignupForm, ResetPasswordForm
from django import forms
from .models import Profile
from django.contrib.auth.models import User

class AllauthSignupForm(SignupForm):
    first_name = forms.CharField(max_length=30, required=True, 
                               widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, required=False, 
                              widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    def save(self, request):
        # First create the user using the parent's save method
        user = super().save(request)
        
        # Then update with our custom fields
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name'] 
        # No need to set is_active=False, allauth does this automatically with mandatory verification
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

