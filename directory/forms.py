from django import forms
from .models import Business, BusinessHours, Service
from django.core.exceptions import ValidationError
import os

class BusinessForm(forms.ModelForm):
    """Form for adding and editing business listings"""
    
    class Meta:
        model = Business
        fields = [
            'name', 'category', 'description', 
            'phone', 'email', 'website',
            'registration_number', 'gst_number'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
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

    def validate_document_file(self, file):
        """Validate uploaded document file (images and PDFs)"""
        if not file:
            return file
        
        # Check file size (5MB max)
        max_size = 5 * 1024 * 1024  # 5MB
        if file.size > max_size:
            raise ValidationError('File size should not exceed 5MB.')
        
        # Check file type
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf']
        if hasattr(file, 'content_type') and file.content_type not in allowed_types:
            raise ValidationError('File must be a JPG, PNG image or PDF document.')
        
        # Check file extension
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.pdf']
        file_extension = os.path.splitext(file.name)[1].lower()
        if file_extension not in allowed_extensions:
            raise ValidationError('File must have .jpg, .jpeg, .png, or .pdf extension.')
        
        return file