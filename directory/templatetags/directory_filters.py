# directory/templatetags/directory_filters.py
from django import template
from directory.utils import extract_youtube_video_id  


register = template.Library()

@register.filter
def filter_by_category(businesses, category_id):
    """Filter businesses by category ID"""
    return businesses.filter(category_id=category_id)

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key"""
    if dictionary and key in dictionary:
        return dictionary[key]
    return None

@register.filter
def split(value, arg):
    """Split a string by the argument and return a list"""
    return value.split(arg)

@register.filter
def get_subscription(user):
    """Get active subscription for a user"""
    from directory.views import get_user_subscription
    return get_user_subscription(user)

@register.filter
def plan_allows(subscription, feature_name):
    """Check if a subscription plan allows a particular feature"""
    if not subscription or not subscription.plan:
        return False
        
    # Free plan limitations
    if subscription.plan.price == 0:
        limited_features = ['business_hours', 'multiple_images', 'leads', 'enquiries', 'reviews', 'verification_badge']
        return feature_name not in limited_features
        
    # Premium plan has all features
    return True

@register.filter
def extract_youtube_id(url):
    """Extract YouTube video ID from URL"""
    return extract_youtube_video_id(url)