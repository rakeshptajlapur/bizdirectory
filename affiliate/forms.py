from django import forms
from .models import AffiliateProfile
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
import os

class AffiliateApplicationForm(forms.ModelForm):
    class Meta:
        model = AffiliateProfile
        fields = ['promotion_strategy', 'aadhar_card', 'pan_card']
        widgets = {
            'promotion_strategy': forms.Textarea(attrs={
                'rows': 4, 
                'placeholder': 'Explain how you plan to promote our business listings...',
                'class': 'form-control'
            }),
            'aadhar_card': forms.FileInput(attrs={
                'accept': 'image/jpeg,image/jpg,image/png',  # Only images
                'class': 'form-control'
            }),
            'pan_card': forms.FileInput(attrs={
                'accept': 'image/jpeg,image/jpg,image/png',  # Only images
                'class': 'form-control'
            })
        }
        labels = {
            'promotion_strategy': 'How will you promote our platform and bring new business owners?',
            'aadhar_card': 'Upload Aadhar Card (Image only)',
            'pan_card': 'Upload PAN Card (Image only)'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make documents required only for new applications
        if not self.instance.pk:
            self.fields['aadhar_card'].required = True
            self.fields['pan_card'].required = True
        else:
            self.fields['aadhar_card'].required = False
            self.fields['pan_card'].required = False

    def clean_aadhar_card(self):
        aadhar_file = self.cleaned_data.get('aadhar_card')
        if aadhar_file and isinstance(aadhar_file, UploadedFile):
            return self.validate_image_file(aadhar_file, 'Aadhar card')
        return aadhar_file

    def clean_pan_card(self):
        pan_file = self.cleaned_data.get('pan_card')
        if pan_file and isinstance(pan_file, UploadedFile):
            return self.validate_image_file(pan_file, 'PAN card')
        return pan_file

    def validate_image_file(self, file, field_name):
        """Validate uploaded image file - FIXED"""
        # Only validate if it's a new upload (UploadedFile instance)
        if not isinstance(file, UploadedFile):
            return file
            
        # Check file size (5MB max)
        max_size = 5 * 1024 * 1024  # 5MB
        if file.size > max_size:
            raise ValidationError(f'{field_name} image size should not exceed 5MB.')
        
        # Check file type - only images
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png']
        if hasattr(file, 'content_type') and file.content_type not in allowed_types:
            raise ValidationError(f'{field_name} must be a JPG or PNG image.')
        
        # Check file extension
        allowed_extensions = ['.jpg', '.jpeg', '.png']
        file_extension = os.path.splitext(file.name)[1].lower()
        if file_extension not in allowed_extensions:
            raise ValidationError(f'{field_name} must have .jpg, .jpeg, or .png extension.')
        
        return file

class KYCDocumentsForm(forms.ModelForm):
    class Meta:
        model = AffiliateProfile
        fields = ['aadhar_card', 'pan_card']
        labels = {
            'aadhar_card': 'Upload Aadhar Card (Image only)',
            'pan_card': 'Upload PAN Card (Image only)'
        }
        widgets = {
            'aadhar_card': forms.FileInput(attrs={
                'accept': 'image/jpeg,image/jpg,image/png',  # Only images
                'class': 'form-control'
            }),
            'pan_card': forms.FileInput(attrs={
                'accept': 'image/jpeg,image/jpg,image/png',  # Only images
                'class': 'form-control'
            })
        }

    def clean_aadhar_card(self):
        aadhar_file = self.cleaned_data.get('aadhar_card')
        if aadhar_file and isinstance(aadhar_file, UploadedFile):
            return self.validate_image_file(aadhar_file, 'Aadhar card')
        return aadhar_file

    def clean_pan_card(self):
        pan_file = self.cleaned_data.get('pan_card')
        if pan_file and isinstance(pan_file, UploadedFile):
            return self.validate_image_file(pan_file, 'PAN card')
        return pan_file

    def validate_image_file(self, file, field_name):
        """Validate uploaded image file - FIXED"""
        # Only validate if it's a new upload (UploadedFile instance)
        if not isinstance(file, UploadedFile):
            return file
            
        # Check file size (5MB max)
        max_size = 5 * 1024 * 1024  # 5MB
        if file.size > max_size:
            raise ValidationError(f'{field_name} image size should not exceed 5MB.')
        
        # Check file type - only images
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png']
        if hasattr(file, 'content_type') and file.content_type not in allowed_types:
            raise ValidationError(f'{field_name} must be a JPG or PNG image.')
        
        # Check file extension
        allowed_extensions = ['.jpg', '.jpeg', '.png']
        file_extension = os.path.splitext(file.name)[1].lower()
        if file_extension not in allowed_extensions:
            raise ValidationError(f'{field_name} must have .jpg, .jpeg, or .png extension.')
        
        return file

class BankDetailsForm(forms.ModelForm):
    class Meta:
        model = AffiliateProfile
        fields = ['account_holder_name', 'bank_name', 'account_number', 'ifsc_code']
        widgets = {
            'account_holder_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'ifsc_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SBIN0001234'})
        }