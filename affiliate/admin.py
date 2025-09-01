from django.contrib import admin
from django.contrib import messages
from .models import AffiliateProfile, AffiliateReferral, AffiliatePayment
import random
import string
import time
from decimal import Decimal
from django.db.models import Sum

@admin.action(description="Approve selected affiliates")
def approve_affiliates(modeladmin, request, queryset):
    count = 0
    for affiliate in queryset.filter(status='pending'):
        # Generate unique 8-character code
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not AffiliateProfile.objects.filter(affiliate_code=code).exists():
                break
        
        affiliate.status = 'approved'
        affiliate.affiliate_code = code
        affiliate.save()
        count += 1
    
    messages.success(request, f"Successfully approved {count} affiliates.")

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
    # FIXED: Only show fields that actually exist in the model
    list_display = ('user', 'status', 'affiliate_code', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__email', 'user__username', 'affiliate_code')
    actions = [approve_affiliates]
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'status', 'affiliate_code')
        }),
        ('Application Details', {
            'fields': ('promotion_strategy',)
        }),
        ('KYC Documents', {
            'fields': ('aadhar_card', 'pan_card')
        }),
        ('Bank Details', {
            'fields': ('account_holder_name', 'bank_name', 'account_number', 'ifsc_code')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

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
