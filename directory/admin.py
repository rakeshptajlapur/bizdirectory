from django.contrib import admin
from django.db.models import Avg
from .models import Category, Business, BusinessImage, BusinessHours, Service, Review, Enquiry, SubscriptionPlan, UserSubscription
from django.utils import timezone
from datetime import timedelta
from django.utils.html import format_html

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'image_preview', 'business_count')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('image_preview',)
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />', obj.image.url)
        return "No image"
    image_preview.short_description = "Image Preview"
    
    def business_count(self, obj):
        return Business.objects.filter(category=obj, is_active=True).count()
    business_count.short_description = "Active Businesses"

@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'is_active', 'gst_verified', 'kyc_status', 'owner')
    list_filter = ('is_active', 'gst_verified', 'kyc_status', 'category')
    search_fields = ('name', 'description', 'address')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('owner', 'name', 'category', 'description', 'is_active')
        }),
        ('Location Information', {
            'fields': ('address', 'pincode', 'city')
        }),
        ('Contact Information', {
            'fields': ('phone', 'email', 'website')
        }),
        ('Business Details', {
            'fields': ('registration_number', 'registration_document')
        }),
        ('Trust & Verification', {
            'fields': ('gst_number', 'gst_document', 'gst_verified', 'kyc_status')
        }),
    )

@admin.register(BusinessImage)
class BusinessImageAdmin(admin.ModelAdmin):
    list_display = ('business', 'caption', 'is_primary')
    list_filter = ('is_primary',)

@admin.register(BusinessHours)
class BusinessHoursAdmin(admin.ModelAdmin):
    list_display = ('business', 'day', 'open_time', 'close_time', 'is_closed')
    list_filter = ('day', 'is_closed')

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('business', 'name')
    search_fields = ('name', 'description')

@admin.action(description="Approve selected reviews")
def approve_reviews(modeladmin, request, queryset):
    queryset.update(is_approved=True)
    
    # Update average ratings for affected businesses
    business_ids = queryset.values_list('business_id', flat=True).distinct()
    for business_id in business_ids:
        business = Business.objects.get(id=business_id)
        # Update business average rating if you store this as a field

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    # Update list_display to include name and email
    list_display = ('business', 'name', 'email', 'rating', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'rating', 'created_at')
    # Add name and email to search fields
    search_fields = ('business__name', 'name', 'email', 'comment')
    actions = [approve_reviews]

@admin.action(description="Mark selected enquiries as responded")
def mark_as_responded(modeladmin, request, queryset):
    queryset.update(is_responded=True)
    modeladmin.message_user(request, f"{queryset.count()} enquiries marked as responded.")

@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ('business', 'name', 'created_at', 'is_responded')
    list_filter = ('is_responded', 'created_at')
    search_fields = ('business__name', 'name', 'email', 'message')
    actions = [mark_as_responded]

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration_days')
    search_fields = ('name',)

@admin.action(description="Verify selected payments")
def verify_payments(modeladmin, request, queryset):
    """Verify selected payments and activate subscriptions"""
    count = 0
    for subscription in queryset:
        if subscription.payment_status == 'pending' and subscription.payment_screenshot:
            subscription.payment_status = 'verified'
            subscription.is_active = True  # Make sure this is set to True
            subscription.save()
            count += 1
    
    messages.success(request, f"Successfully verified {count} payments.")

@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'start_date', 'expiry_date', 'payment_status', 'is_active', 'has_payment_screenshot')
    list_filter = ('plan', 'payment_status', 'is_active')
    search_fields = ('user__username', 'user__email')
    actions = [verify_payments]
    
    # Enhanced fields display
    fields = (
        'user', 'plan', 'business', 'affiliate_code',
        'start_date', 'expiry_date', 
        'payment_status', 'is_active',
        'payment_screenshot_display', 'payment_screenshot'
    )
    
    readonly_fields = ('start_date', 'payment_screenshot_display')
    
    def has_payment_screenshot(self, obj):
        return bool(obj.payment_screenshot)
    has_payment_screenshot.boolean = True
    has_payment_screenshot.short_description = "Has Receipt"
    
    def payment_screenshot_display(self, obj):
        if obj.payment_screenshot:
            file_url = obj.payment_screenshot.url
            file_name = obj.payment_screenshot.name.split('/')[-1]
            
            # Check if it's a PDF
            if file_name.lower().endswith('.pdf'):
                return format_html(
                    '<div style="margin: 10px 0;">'
                    '<p><strong>📄 PDF Receipt:</strong> {}</p>'
                    '<a href="{}" target="_blank" class="button" style="background: #007cba; color: white; padding: 8px 12px; text-decoration: none; border-radius: 4px;">'
                    '📄 Open PDF Receipt</a>'
                    '</div>',
                    file_name, file_url
                )
            else:
                # It's an image
                return format_html(
                    '<div style="margin: 10px 0;">'
                    '<p><strong>🖼️ Payment Screenshot:</strong></p>'
                    '<img src="{}" style="max-width: 300px; max-height: 200px; border: 1px solid #ddd; border-radius: 4px;" /><br>'
                    '<a href="{}" target="_blank" class="button" style="background: #007cba; color: white; padding: 8px 12px; text-decoration: none; border-radius: 4px; margin-top: 10px; display: inline-block;">'
                    '🔍 View Full Size</a>'
                    '</div>',
                    file_url, file_url
                )
        return "No receipt uploaded"
    
    payment_screenshot_display.short_description = "Payment Receipt"
