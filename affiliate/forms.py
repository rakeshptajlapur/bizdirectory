from django import forms
from .models import AffiliateProfile

class AffiliateApplicationForm(forms.ModelForm):
    class Meta:
        model = AffiliateProfile
        fields = ['promotion_strategy', 'aadhar_card', 'pan_card']
        widgets = {
            'promotion_strategy': forms.Textarea(attrs={
                'rows': 4, 
                'placeholder': 'Explain how you plan to promote our business listings...'
            }),
            'aadhar_card': forms.FileInput(attrs={
                'accept': 'image/*,application/pdf',
                'required': True
            }),
            'pan_card': forms.FileInput(attrs={
                'accept': 'image/*,application/pdf', 
                'required': True
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
        widgets = {
            'aadhar_card': forms.FileInput(attrs={'accept': 'image/*,application/pdf'}),
            'pan_card': forms.FileInput(attrs={'accept': 'image/*,application/pdf'})
        }