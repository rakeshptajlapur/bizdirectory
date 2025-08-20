from django.db import models
from django.contrib.auth.models import User

class AffiliateProfile(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='affiliate_profile')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    promotion_strategy = models.TextField(blank=True)
    affiliate_code = models.CharField(max_length=8, unique=True, blank=True, null=True)
    
    # Bank details
    account_holder_name = models.CharField(max_length=100, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=20, blank=True)
    ifsc_code = models.CharField(max_length=20, blank=True)
    
    # KYC documents
    aadhar_card = models.FileField(upload_to='affiliate_documents/aadhar/', blank=True, null=True)
    pan_card = models.FileField(upload_to='affiliate_documents/pan/', blank=True, null=True)
    
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pending_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Affiliate: {self.user.email}"

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
        return f"Referral by {self.affiliate.user.email} for {self.subscription.business.name if self.subscription.business else 'Unknown Business'}"

class AffiliatePayment(models.Model):
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold')
    ]
    
    affiliate = models.ForeignKey(AffiliateProfile, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"Payment of ₹{self.amount} to {self.affiliate.user.email}"
