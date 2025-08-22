from django.core.cache import cache
from django.db.models import Count, Q, Avg
from .models import Category, Business

def get_cached_categories():
    """Get categories with caching"""
    cache_key = 'home_categories'
    categories = cache.get(cache_key)
    
    if categories is None:
        categories = list(Category.objects.annotate(
            business_count=Count('business', filter=Q(business__is_active=True))
        ).filter(business_count__gt=0)[:8])
        cache.set(cache_key, categories, 300)  # Cache for 5 minutes
    
    return categories

def get_cached_featured_businesses():
    """Get featured businesses with caching"""
    cache_key = 'featured_businesses'
    businesses = cache.get(cache_key)
    
    if businesses is None:
        businesses = list(Business.objects.select_related(
            'category', 'owner'
        ).prefetch_related(
            'images'
        ).filter(
            is_active=True
        ).annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        )[:8])
        cache.set(cache_key, businesses, 600)  # Cache for 10 minutes
    
    return businesses