from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='category_images/', blank=True, null=True)
    
    # Add this method for fallback images
    def get_image_url(self):
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        else:
            # Fallback images dictionary - map category IDs to default images
            fallback_images = {
                1: "https://images.unsplash.com/photo-1607472586893-edb57bdc0e39?ixlib=rb-1.2.1&auto=format&fit=crop&w=1000&q=80",  # Plumbing
                2: "https://images.unsplash.com/photo-1524178232363-1fb2b075b655?ixlib=rb-1.2.1&auto=format&fit=crop&w=1000&q=80",  # Training
                3: "https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?ixlib=rb-1.2.1&auto=format&fit=crop&w=1000&q=80",  # Hospitals
                4: "https://images.unsplash.com/photo-1546410531-bb4caa6b424d?ixlib=rb-1.2.1&auto=format&fit=crop&w=1000&q=80",     # Schools
                5: "https://images.unsplash.com/photo-1544724107-6d5c4caaff30?ixlib=rb-1.2.1&auto=format&fit=crop&w=1000&q=80",     # Electricians
            }
            return fallback_images.get(self.id, "https://via.placeholder.com/500x300?text=No+Image")
    
    class Meta:
        verbose_name_plural = "Categories"
        
    def __str__(self):
        return self.name

class Business(models.Model):
    # Basic Info
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    description = models.TextField()
    
    # Location Info
    address = models.TextField()
    pincode = models.CharField(max_length=6)
    city = models.CharField(max_length=100)
    
    # Contact Info
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    website = models.URLField(blank=True)
    
    # Business Details (Non-public)
    registration_number = models.CharField(max_length=50)
    gst_number = models.CharField(max_length=15, blank=True)
    gst_verified = models.BooleanField(default=False)
    kyc_status = models.CharField(
        max_length=20,
        choices=[
            ('completed', 'Completed'),
            ('pending', 'Pending'),
            ('not_submitted', 'Not Submitted')
        ],
        default='not_submitted'
    )
    registration_document = models.FileField(upload_to='documents/')
    
    # Meta Info
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = "Businesses"
        
    def __str__(self):
        return self.name

    def get_primary_image(self):
        return self.images.filter(is_primary=True).first()

    def get_primary_image_url(self):
        primary_image = self.get_primary_image()
        if (primary_image and hasattr(primary_image.image, 'url')):
            return primary_image.image.url
        else:
            # Fallback images based on business category
            category_fallbacks = {
                1: "https://images.unsplash.com/photo-1607472586893-edb57bdc0e39",  # Plumbing
                2: "https://images.unsplash.com/photo-1524178232363-1fb2b075b655",  # Training
                3: "https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d",  # Hospitals
                4: "https://images.unsplash.com/photo-1546410531-bb4caa6b424d",  # Schools
                5: "https://images.unsplash.com/photo-1544724107-6d5c4caaff30",  # Electricians
            }
            category_id = self.category_id if self.category_id else 0
            return category_fallbacks.get(category_id, 
                f"https://via.placeholder.com/500x300?text={self.name.replace(' ', '+')}") + "?ixlib=rb-1.2.1&auto=format&fit=crop&w=500&q=80"

class BusinessImage(models.Model):
    business = models.ForeignKey(Business, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='business_images/')
    caption = models.CharField(max_length=100, blank=True)
    is_primary = models.BooleanField(default=False)

class BusinessHours(models.Model):
    DAYS_OF_WEEK = [
        (1, 'Monday'),
        (2, 'Tuesday'),
        (3, 'Wednesday'),
        (4, 'Thursday'),
        (5, 'Friday'),
        (6, 'Saturday'),
        (7, 'Sunday'),
    ]
    
    business = models.ForeignKey(Business, related_name='hours', on_delete=models.CASCADE)
    day = models.IntegerField(choices=DAYS_OF_WEEK)
    open_time = models.TimeField()
    close_time = models.TimeField()
    is_closed = models.BooleanField(default=False)

class Service(models.Model):
    business = models.ForeignKey(Business, related_name='services', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

class Review(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='reviews')
    # Keep the user field for future auth, but make it nullable
    user = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='reviews', 
                            null=True, blank=True)
    # Add fields for non-authenticated users
    name = models.CharField(max_length=100)
    email = models.EmailField()
    
    # Existing fields
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Review by {self.name} for {self.business.name}"

class Enquiry(models.Model):
    business = models.ForeignKey(Business, related_name='enquiries', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_responded = models.BooleanField(default=False)

class CouponRequest(models.Model):
    """Model for tracking discount coupon requests"""
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='coupon_requests')
    email = models.EmailField()
    coupon_code = models.CharField(max_length=20, blank=True, null=True)
    is_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Coupon request from {self.email} for {self.business.name}"
