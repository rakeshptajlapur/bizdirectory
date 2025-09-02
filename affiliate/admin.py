from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import ValidationError
from .models import AffiliateProfile, AffiliateReferral, AffiliatePayment
import random
import string
import time
from decimal import Decimal
from django.db.models import Sum

@admin.action(description="Approve selected affiliates")
def approve_affiliates(modeladmin, request, queryset):
    """Approve affiliates - but they still need affiliate codes to be manually set"""
    count = 0
    errors = []
    
    for affiliate in queryset.filter(status='pending'):
        # Check if affiliate code is set
        if not affiliate.affiliate_code or affiliate.affiliate_code.strip() == '':
            errors.append(f"{affiliate.user.get_full_name() or affiliate.user.username} - Missing affiliate code")
            continue
            
        # Validate affiliate code format and uniqueness
        code = affiliate.affiliate_code.strip().upper()
        if len(code) < 6 or len(code) > 12:
            errors.append(f"{affiliate.user.get_full_name() or affiliate.user.username} - Code must be 6-12 characters")
            continue
            
        # Check for duplicate codes
        if AffiliateProfile.objects.filter(affiliate_code=code).exclude(id=affiliate.id).exists():
            errors.append(f"{affiliate.user.get_full_name() or affiliate.user.username} - Code '{code}' already exists")
            continue
        
        # Approve the affiliate
        affiliate.status = 'approved'
        affiliate.affiliate_code = code
        affiliate.save()
        count += 1
    
    # Show results
    if count > 0:
        messages.success(request, f"Successfully approved {count} affiliates.")
    
    if errors:
        error_message = "Issues found:\n" + "\n".join(errors)
        messages.error(request, error_message)

@admin.action(description="Mark selected payments as completed")
def process_payments(modeladmin, request, queryset):
    completed_count = 0
    for payment in queryset.filter(status='processing'):
        payment.status = 'completed'
        
        # Add transaction ID if not present
        if not payment.transaction_id:
            payment.transaction_id = f"TXN-{int(time.time())}-{payment.id}"
        
        payment.save()
        completed_count += 1
    
    messages.success(request, f"Successfully processed {completed_count} payment(s).")

@admin.action(description="Approve selected referrals")
def approve_referrals(modeladmin, request, queryset):
    queryset.update(status='approved')
    messages.success(request, f"Successfully approved {queryset.count()} referrals.")

@admin.action(description="Reject selected referrals")
def reject_referrals(modeladmin, request, queryset):
    queryset.update(status='rejected')
    messages.success(request, f"Successfully rejected {queryset.count()} referrals.")

@admin.register(AffiliateProfile)
class AffiliateProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'affiliate_code', 'get_total_earnings', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__email', 'user__username', 'affiliate_code')
    actions = [approve_affiliates]
    readonly_fields = ('created_at', 'updated_at', 'get_total_earnings')
    
    def get_total_earnings(self, obj):
        """Get total earnings for display"""
        try:
            return f"₹{obj.total_earnings}"
        except:
            return "₹0.00"
    get_total_earnings.short_description = 'Total Earnings'
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'status'),
            'description': 'Basic user and approval information'
        }),
        ('Affiliate Code', {
            'fields': ('affiliate_code',),
            'description': '''
                <strong>IMPORTANT:</strong> Enter a unique affiliate code (6-12 characters, letters and numbers only).<br>
                • Examples: AFFIL001, BIZ2024, REFER123<br>
                • This code will be used by businesses to get referral discounts<br>
                • Code must be unique across all affiliates<br>
                • <span style="color: red;">Required before approving status!</span>
            '''
        }),
        ('Application Details', {
            'fields': ('promotion_strategy',),
            'description': 'How the affiliate plans to promote the platform'
        }),
        ('KYC Documents', {
            'fields': ('aadhar_card', 'pan_card'),
            'description': 'Identity verification documents uploaded by affiliate'
        }),
        ('Bank Details', {
            'fields': ('account_holder_name', 'bank_name', 'account_number', 'ifsc_code'),
            'description': 'Bank account information for commission payouts'
        }),
        ('Earnings', {
            'fields': ('get_total_earnings',),
            'classes': ('collapse',),
            'description': 'Commission earnings summary (auto-calculated)'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Custom save with validation"""
        if obj.status == 'approved' and (not obj.affiliate_code or obj.affiliate_code.strip() == ''):
            messages.error(request, "Cannot approve affiliate without setting an affiliate code!")
            return
        
        if obj.affiliate_code:
            obj.affiliate_code = obj.affiliate_code.strip().upper()
        
        super().save_model(request, obj, form, change)

@admin.register(AffiliateReferral)
class AffiliateReferralAdmin(admin.ModelAdmin):
    list_display = ('affiliate', 'get_business_name', 'commission_amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    actions = [approve_referrals, reject_referrals] 
    
    def get_business_name(self, obj):
        if obj.subscription and obj.subscription.business:
            return obj.subscription.business.name
        return "Unknown Business"
    get_business_name.short_description = "Business"
    
@admin.register(AffiliatePayment)
class AffiliatePaymentAdmin(admin.ModelAdmin):
    list_display = ('affiliate', 'amount', 'status', 'payment_date')
    list_filter = ('status', 'payment_date')
    actions = [process_payments]
