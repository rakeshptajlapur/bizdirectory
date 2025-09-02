from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
import uuid
import re

class AffiliateProfile(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='affiliate_profile')
    affiliate_code = models.CharField(
        max_length=20, 
        unique=True, 
        blank=True, 
        null=True,
        help_text="Unique referral code (6-12 characters, letters and numbers only). Required for approval."
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Application details
    promotion_strategy = models.TextField(help_text="How will you promote BizDirectory?")
    
    # KYC Documents
    aadhar_card = models.FileField(upload_to='affiliate_documents/aadhar/', blank=True, null=True)
    pan_card = models.FileField(upload_to='affiliate_documents/pan/', blank=True, null=True)
    
    # Bank Details for payouts
    account_holder_name = models.CharField(max_length=100, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=20, blank=True)
    ifsc_code = models.CharField(max_length=11, blank=True, help_text="11-digit alphanumeric IFSC code")
    
    # ADD THESE FIELDS - they exist in your database
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    pending_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    paid_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def clean(self):
        """Model validation"""
        super().clean()
        
        # Validate affiliate code format if provided
        if self.affiliate_code:
            code = self.affiliate_code.strip().upper()
            
            # Check length
            if len(code) < 6 or len(code) > 12:
                raise ValidationError({'affiliate_code': 'Affiliate code must be 6-12 characters long.'})
            
            # Check format (letters and numbers only)
            if not re.match(r'^[A-Z0-9]+$', code):
                raise ValidationError({'affiliate_code': 'Affiliate code can only contain letters and numbers.'})
            
            self.affiliate_code = code
        
        # Check if trying to approve without affiliate code
        if self.status == 'approved' and (not self.affiliate_code or self.affiliate_code.strip() == ''):
            raise ValidationError({'affiliate_code': 'Affiliate code is required when status is approved.'})
    
    def save(self, *args, **kwargs):
        # Run validation
        self.clean()
        
        # Ensure earnings fields are never None
        if self.total_earnings is None:
            self.total_earnings = Decimal('0.00')
        if self.pending_earnings is None:
            self.pending_earnings = Decimal('0.00')
        if self.paid_earnings is None:
            self.paid_earnings = Decimal('0.00')
        
        # Only generate code when approved and doesn't have one
        if self.status == 'approved' and not self.affiliate_code:
            self.affiliate_code = self.generate_affiliate_code()
        super().save(*args, **kwargs)
    
    def generate_affiliate_code(self):
        """Generate unique affiliate code"""
        while True:
            code = f"AFF{str(uuid.uuid4())[:8].upper()}"
            if not AffiliateProfile.objects.filter(affiliate_code=code).exists():
                return code
    
    def calculate_earnings(self):
        """Calculate total earnings from approved referrals"""
        from django.db.models import Sum
        total = self.referrals.filter(status='approved').aggregate(
            total=Sum('commission_amount')
        )['total'] or Decimal('0.00')
        
        # Update the stored total_earnings
        if self.total_earnings != total:
            self.total_earnings = total
            self.save(update_fields=['total_earnings'])
        
        return total
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.status}"
    
    class Meta:
        verbose_name = "Affiliate Profile"
        verbose_name_plural = "Affiliate Profiles"

class AffiliateReferral(models.Model):
    STATUS_CHOICES = [
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    affiliate = models.ForeignKey(AffiliateProfile, on_delete=models.CASCADE, related_name='referrals')
    subscription = models.ForeignKey('directory.UserSubscription', on_delete=models.CASCADE)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_approval')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.affiliate.user.username} - ₹{self.commission_amount} - {self.status}"

class AffiliatePayment(models.Model):
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
    ]
    
    affiliate = models.ForeignKey(AffiliateProfile, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.affiliate.user.username} - ₹{self.amount} - {self.status}"
