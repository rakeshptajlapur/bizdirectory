from django import forms
from .models import Business, BusinessHours, Service
from django.core.exceptions import ValidationError
import os
import re

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
            'description': forms.Textarea(attrs={
                'rows': 4, 
                'class': 'form-control',
                'maxlength': '1000',
                'minlength': '50'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '100',
                'minlength': '3'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'pattern': '^[6-9][0-9]{9}$',
                'maxlength': '10',
                'placeholder': '9876543210'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'business@example.com'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://www.example.com'
            }),
            'registration_number': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '50',
                'minlength': '4',
                'placeholder': 'U12345MH2020PTC123456'
            }),
            'gst_number': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '15',
                'minlength': '15',
                'pattern': '^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$',
                'placeholder': '27AAPFU0939F1ZV'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Make category a dropdown
        self.fields['category'].widget.attrs.update({'class': 'form-select'})
        
        # Add validation messages
        self.fields['phone'].error_messages = {
            'invalid': 'Enter a valid 10-digit mobile number starting with 6, 7, 8, or 9.'
        }
        self.fields['gst_number'].error_messages = {
            'invalid': 'Enter a valid 15-character GST number (e.g., 27AAPFU0939F1ZV).'
        }
        
        # Pre-populate contact info from user profile if empty
        if self.user and not self.instance.pk:
            self.fields['email'].initial = self.user.email
            if hasattr(self.user, 'profile') and self.user.profile.phone:
                self.fields['phone'].initial = self.user.profile.phone

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            # Remove any non-digit characters
            phone = ''.join(filter(str.isdigit, phone))
            
            # Validate Indian mobile number
            if not re.match(r'^[6-9][0-9]{9}$', phone):
                raise forms.ValidationError('Enter a valid 10-digit mobile number starting with 6, 7, 8, or 9.')
        return phone

    def clean_gst_number(self):
        gst_number = self.cleaned_data.get('gst_number')
        if gst_number:
            # Remove spaces and convert to uppercase
            gst_number = gst_number.replace(' ', '').upper()
            
            # Validate GST number format
            if not re.match(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$', gst_number):
                raise forms.ValidationError('Enter a valid 15-character GST number (e.g., 27AAPFU0939F1ZV).')
        return gst_number

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