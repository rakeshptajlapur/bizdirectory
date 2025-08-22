from django import template
from django.core.cache import cache
from django.db.models import Avg, Count
from ..models import Business

register = template.Library()

@register.simple_tag
def get_business_rating(business):
    """Get cached business rating"""
    cache_key = f'business_rating_{business.id}'
    rating = cache.get(cache_key)
    
    if rating is None:
        rating = business.reviews.aggregate(
            avg_rating=Avg('rating'),
            count=Count('id')
        )
        cache.set(cache_key, rating, 300)  # Cache for 5 minutes
    
    return rating

@register.simple_tag
def get_business_review_count(business):
    """Get cached review count"""
    cache_key = f'business_reviews_{business.id}'
    count = cache.get(cache_key)
    
    if count is None:
        count = business.reviews.filter(is_approved=True).count()
        cache.set(cache_key, count, 300)
    
    return count