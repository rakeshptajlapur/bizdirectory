from django.contrib import admin
from django.contrib import messages
from .models import AffiliateProfile, AffiliateReferral, AffiliatePayment
import random
import string

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

@admin.action(description="Process selected payments")
def process_payments(modeladmin, request, queryset):
    for payment in queryset.filter(status='processing'):
        payment.status = 'completed'
        payment.save()
        
        # Update affiliate earnings
        affiliate = payment.affiliate
        affiliate.paid_earnings += payment.amount
        affiliate.pending_earnings -= payment.amount
        affiliate.save()

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
    list_display = ('user', 'status', 'affiliate_code', 'total_earnings', 'pending_earnings')
    list_filter = ('status',)
    search_fields = ('user__email', 'user__username', 'affiliate_code')
    actions = [approve_affiliates]

@admin.register(AffiliateReferral)
class AffiliateReferralAdmin(admin.ModelAdmin):
    list_display = ('affiliate', 'get_business_name', 'commission_amount', 'status', 'created_at')
    list_filter = ('status',)
    actions = [approve_referrals, reject_referrals]
    
    def get_business_name(self, obj):
        return obj.subscription.business.name if obj.subscription.business else "Unknown Business"
    get_business_name.short_description = "Business"
    
@admin.register(AffiliatePayment)
class AffiliatePaymentAdmin(admin.ModelAdmin):
    list_display = ('affiliate', 'amount', 'status', 'payment_date')
    list_filter = ('status',)
    actions = [process_payments]
