from django.contrib import admin
from .models import Category, Business, BusinessImage, BusinessHours, Service, Review, Enquiry

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'is_active', 'gst_verified', 'kyc_status')
    list_filter = ('is_active', 'gst_verified', 'kyc_status', 'category')
    search_fields = ('name', 'description', 'address')
    
    fieldsets = (
        ('Trust & Verification', {
            'fields': ('gst_number', 'gst_verified', 'kyc_status')
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

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('business', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')

@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ('business', 'name', 'created_at', 'is_responded')
    list_filter = ('is_responded', 'created_at')
