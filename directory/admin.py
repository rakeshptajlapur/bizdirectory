from django.contrib import admin
from django.db.models import Avg
from .models import Category, Business, BusinessImage, BusinessHours, Service, Review, Enquiry

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

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
