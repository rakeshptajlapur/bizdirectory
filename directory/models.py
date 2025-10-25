from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from cloudinary_storage.storage import MediaCloudinaryStorage

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(
        upload_to='category_images/', 
        blank=True, 
        null=True,
        storage=MediaCloudinaryStorage()  # ✅ ADD CLOUDINARY STORAGE
    )
    
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
    city = models.CharField(max_length=100, blank=True, default='')  # Keep this field
    state = models.CharField(max_length=100, blank=True, default='')
    
    # Google Maps location fields
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_name = models.CharField(max_length=255, blank=True, default='')
    place_id = models.CharField(max_length=255, blank=True, default='')
    formatted_address = models.TextField(blank=True, default='')
    
    # Contact Info
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    website = models.URLField(blank=True)
    
    # Business Details (Non-public)
    registration_number = models.CharField(max_length=50)
    registration_document = models.FileField(
        upload_to='documents/',
        storage=MediaCloudinaryStorage()  # Force Cloudinary
    )
    gst_number = models.CharField(max_length=15, blank=True)
    gst_document = models.FileField(
        upload_to='gst_documents/', 
        null=True, 
        blank=True,
        storage=MediaCloudinaryStorage()  # Force Cloudinary
    )  # New field
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
    # ...other fields...

    # Meta Info
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    # Whether the listing has been approved by an admin
    is_approved = models.BooleanField(default=False)

    # Add these fields to track subscription status
    subscription_plan = models.ForeignKey(
        'SubscriptionPlan', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='businesses'
    )
    
    # Coupon settings
    coupon_enabled = models.BooleanField(default=True, help_text="Enable coupon requests for this business")
    coupon_discount = models.IntegerField(default=20, help_text="Discount percentage for coupons (5-50%)", 
                                        validators=[MinValueValidator(5), MaxValueValidator(50)])

    class Meta:
        verbose_name_plural = "Businesses"
        
    def __str__(self):
        return self.name

    def get_primary_image(self):
        return self.images.filter(is_primary=True).first()

    def get_primary_image_url(self):
        primary_image = self.get_primary_image()
        try:
            if (primary_image and hasattr(primary_image.image, 'url')):
                # Try to access the URL - if it fails, we'll use the fallback
                url = primary_image.image.url
                return url
        except (ValueError, AttributeError, IOError) as e:
            # Log the error but continue to fallback
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error retrieving image URL for business {self.id}: {str(e)}")
    
        # Using only 3 high-quality landscape model images as fallbacks
        portrait_fallbacks = [
            "https://images.unsplash.com/photo-1534528741775-53994a69daeb?ixlib=rb-1.2.1&auto=format&fit=crop&w=1000&h=600&q=80", # Professional female model with blue background
            "https://images.unsplash.com/photo-1529626455594-4ff0802cfb7e?ixlib=rb-1.2.1&auto=format&fit=crop&w=1000&h=600&q=80", # Female model in casual outfit, landscape orientation
            "https://images.unsplash.com/photo-1488161628813-04466f872be2?ixlib=rb-1.2.1&auto=format&fit=crop&w=1000&h=600&q=80", # Professional model portrait in landscape format
        ]
        
        # Use business ID to deterministically select a fallback image
        # This ensures the same business always gets the same fallback image
        fallback_index = self.id % len(portrait_fallbacks)
        return portrait_fallbacks[fallback_index]

    @property
    def has_premium_features(self):
        """Check if business has premium features"""
        subscription = UserSubscription.objects.filter(
            business=self, 
            is_active=True,
            expiry_date__gt=timezone.now()
        ).first()
        
        if subscription and subscription.plan.price > 0:
            return True
        return False

    def get_related_businesses(self, limit=6):
        """Get related businesses in the same category, excluding current business"""
        return Business.objects.filter(
            category=self.category,
            is_active=True
        ).exclude(
            id=self.id
        ).order_by('-created_at')[:limit]

class BusinessImage(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(
        upload_to='business_images/',
        storage=MediaCloudinaryStorage()  # Force Cloudinary
    )
    caption = models.CharField(max_length=200, blank=True)
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
    discount_percentage = models.IntegerField(default=20, help_text="Discount percentage (e.g., 20 for 20%)")
    is_sent = models.BooleanField(default=False, help_text="Email sent to customer")
    is_fulfilled = models.BooleanField(default=False, help_text="Coupon used by customer")
    fulfilled_at = models.DateTimeField(null=True, blank=True, help_text="When the coupon was used")
    notes = models.TextField(blank=True, help_text="Internal notes about this coupon")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Coupon {self.coupon_code} for {self.business.name} - {self.email}"

# Add these new models at the end

class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)  # "Free", "Premium"
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    features = models.TextField()  # Store features as comma-separated list
    duration_days = models.IntegerField(default=365)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class UserSubscription(models.Model):
    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Payment Pending'),
        ('verified', 'Payment Verified'),
        ('expired', 'Expired')
    )
    
    # Add this field to link subscription to business
    business = models.OneToOneField(Business, on_delete=models.CASCADE, null=True, blank=True, related_name='subscription')
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    start_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField()
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    # ✅ UPDATE: Add Cloudinary storage to payment_screenshot
    payment_screenshot = models.FileField(
        upload_to='payment_screenshots/', 
        blank=True, 
        null=True,
        storage=MediaCloudinaryStorage()  # Force Cloudinary for payment screenshots
    )
    
    is_active = models.BooleanField(default=False)  # Only active after admin verification
    affiliate_code = models.CharField(max_length=8, blank=True, null=True)
    
    def is_expired(self):
        return timezone.now() > self.expiry_date
    
    def days_remaining(self):
        if self.is_expired():
            return 0
        delta = self.expiry_date - timezone.now()
        return delta.days
    
    @property
    def commission_earned(self):
        """Calculate 20% commission on plan price"""
        if self.plan:
            return float(self.plan.price) * 0.20
        return 0
    
    def __str__(self):
        return f"{self.user.username}'s {self.plan.name} subscription"
