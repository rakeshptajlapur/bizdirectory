from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

class AffiliateProfile(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='affiliate_profile')
    affiliate_code = models.CharField(max_length=20, unique=True, blank=True, null=True)
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
    # FIXED: Set IFSC code to exactly 11 characters (standard IFSC length)
    ifsc_code = models.CharField(max_length=11, blank=True, help_text="11-digit alphanumeric IFSC code")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
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
