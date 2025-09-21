from django import forms
from .models import Business, BusinessHours, Service
from django.core.exceptions import ValidationError

class BusinessForm(forms.ModelForm):
    """Form for adding and editing business listings"""
    
    class Meta:
        model = Business
        fields = [
            'name', 'category', 'description', 
            # REMOVED: 'address', 'city', 'pincode',  # Remove old location fields
            'phone', 'email', 'website',
            'registration_number', 'gst_number'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            # REMOVED: 'address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            # REMOVED: 'city': forms.TextInput(attrs={'class': 'form-control'}),
            # REMOVED: 'pincode': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'gst_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Make category a dropdown
        self.fields['category'].widget.attrs.update({'class': 'form-select'})
        
        # Pre-populate contact info from user profile if empty
        if self.user and not self.instance.pk:
            self.fields['email'].initial = self.user.email
            if hasattr(self.user, 'profile') and self.user.profile.phone:
                self.fields['phone'].initial = self.user.profile.phone