from django import forms
from django.core.exceptions import ValidationError
from .models import AffiliateProfile
import re
import os

class AffiliateApplicationForm(forms.ModelForm):
    class Meta:
        model = AffiliateProfile
        fields = ['promotion_strategy', 'aadhar_card', 'pan_card']
        # Note: Excluding total_earnings from form as it's auto-calculated
        widgets = {
            'promotion_strategy': forms.Textarea(attrs={
                'rows': 4, 
                'placeholder': 'Explain how you plan to promote our business listings...',
                'class': 'form-control'
            }),
            'aadhar_card': forms.FileInput(attrs={
                'accept': 'image/*,application/pdf',
                'class': 'form-control'
            }),
            'pan_card': forms.FileInput(attrs={
                'accept': 'image/*,application/pdf',
                'class': 'form-control'
            })
        }
        labels = {
            'promotion_strategy': 'How will you promote our platform and bring new business owners?',
            'aadhar_card': 'Upload Aadhar Card (PDF/Image)',
            'pan_card': 'Upload PAN Card (PDF/Image)'
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
        if aadhar_file:
            return self.validate_file(aadhar_file, 'Aadhar card')
        return aadhar_file

    def clean_pan_card(self):
        pan_file = self.cleaned_data.get('pan_card')
        if pan_file:
            return self.validate_file(pan_file, 'PAN card')
        return pan_file

    def validate_file(self, file, field_name):
        """Validate uploaded file"""
        # Check file size (5MB max)
        max_size = 5 * 1024 * 1024  # 5MB
        if file.size > max_size:
            raise ValidationError(f'{field_name} file size should not exceed 5MB.')
        
        # Check file type
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf']
        if file.content_type not in allowed_types:
            raise ValidationError(f'{field_name} must be a JPG, PNG, or PDF file.')
        
        # Check file extension
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.pdf']
        file_extension = os.path.splitext(file.name)[1].lower()
        if file_extension not in allowed_extensions:
            raise ValidationError(f'{field_name} must have .jpg, .png, or .pdf extension.')
        
        return file

class BankDetailsForm(forms.ModelForm):
    class Meta:
        model = AffiliateProfile
        fields = ['account_holder_name', 'bank_name', 'account_number', 'ifsc_code']
        widgets = {
            'account_holder_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_number': forms.TextInput(attrs={
                'placeholder': 'Enter your account number',
                'class': 'form-control'
            }),
            'ifsc_code': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '11',
                'placeholder': 'SBIN0001234',
                'style': 'text-transform: uppercase;'
            })
        }
        labels = {
            'account_holder_name': 'Account Holder Name',
            'bank_name': 'Bank Name',
            'account_number': 'Account Number',
            'ifsc_code': 'IFSC Code'
        }
    
    def clean_ifsc_code(self):
        ifsc_code = self.cleaned_data.get('ifsc_code', '').upper()
        
        if ifsc_code:
            # IFSC format: 4 letters + 0 + 6 alphanumeric characters
            ifsc_pattern = r'^[A-Z]{4}0[A-Z0-9]{6}$'
            
            if len(ifsc_code) != 11:
                raise forms.ValidationError("IFSC code must be exactly 11 characters long.")
            
            if not re.match(ifsc_pattern, ifsc_code):
                raise forms.ValidationError("Invalid IFSC code format. Example: SBIN0001234")
        
        return ifsc_code

class KYCDocumentsForm(forms.ModelForm):
    class Meta:
        model = AffiliateProfile
        fields = ['aadhar_card', 'pan_card']
        labels = {
            'aadhar_card': 'Upload Aadhar Card (PDF/Image)',
            'pan_card': 'Upload PAN Card (PDF/Image)'
        }
        widgets = {
            'aadhar_card': forms.FileInput(attrs={
                'accept': 'image/*,application/pdf',
                'class': 'form-control'
            }),
            'pan_card': forms.FileInput(attrs={
                'accept': 'image/*,application/pdf',
                'class': 'form-control'
            })
        }