from django.db.models.signals import post_save
from django.dispatch import receiver
from directory.models import UserSubscription
from .models import AffiliateProfile, AffiliateReferral
from decimal import Decimal  # Add this import at the top

@receiver(post_save, sender=UserSubscription)
def process_affiliate_commission(sender, instance, **kwargs):
    """Process commission when a subscription is verified"""
    # Only process active subscriptions with affiliate codes
    if instance.is_active and instance.payment_status == 'verified' and instance.affiliate_code:
        try:
            affiliate = AffiliateProfile.objects.get(affiliate_code=instance.affiliate_code)
            
            # Check if referral already exists
            existing_referral = AffiliateReferral.objects.filter(
                affiliate=affiliate,
                subscription=instance
            ).exists()
            
            if not existing_referral:
                # Calculate 20% commission - Convert to Decimal before adding
                commission = Decimal(str(float(instance.plan.price) * 0.20))
                
                # Create referral record
                referral = AffiliateReferral.objects.create(
                    affiliate=affiliate,
                    subscription=instance,
                    commission_amount=commission,
                    status='pending_approval'  # Changed from 'pending' to 'pending_approval'
                )
                
                # Update affiliate earnings
                affiliate.total_earnings += commission
                affiliate.pending_earnings += commission
                affiliate.save()
        
        except AffiliateProfile.DoesNotExist:
            # Invalid affiliate code, do nothing
            pass