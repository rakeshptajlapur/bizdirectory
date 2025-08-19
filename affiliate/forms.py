from django import forms
from .models import AffiliateProfile

class AffiliateApplicationForm(forms.ModelForm):
    class Meta:
        model = AffiliateProfile
        fields = ['promotion_strategy']
        widgets = {
            'promotion_strategy': forms.Textarea(attrs={
                'rows': 4, 
                'placeholder': 'Explain how you plan to promote our business listings...'
            })
        }
        labels = {
            'promotion_strategy': 'How will you promote our platform and bring new business owners?'
        }

class BankDetailsForm(forms.ModelForm):
    class Meta:
        model = AffiliateProfile
        fields = ['account_holder_name', 'bank_name', 'account_number', 'ifsc_code']
        widgets = {
            'account_number': forms.TextInput(attrs={'placeholder': 'Enter your account number'})
        }

class KYCDocumentsForm(forms.ModelForm):
    class Meta:
        model = AffiliateProfile
        fields = ['aadhar_card', 'pan_card']
        labels = {
            'aadhar_card': 'Upload Aadhar Card (PDF/Image)',
            'pan_card': 'Upload PAN Card (PDF/Image)'
        }