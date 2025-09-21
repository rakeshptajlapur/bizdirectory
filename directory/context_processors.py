from django.conf import settings

def cloudinary_settings(request):
    return {
        'CLOUDINARY_SETTINGS': settings.CLOUDINARY_STORAGE
    }

def google_maps_key(request):
    """Make Google Maps API key available in all templates"""
    return {
        'GOOGLE_MAPS_API_KEY': getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
    }