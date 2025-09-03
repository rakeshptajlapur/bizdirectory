from django.conf import settings

def cloudinary_settings(request):
    return {
        'CLOUDINARY_SETTINGS': settings.CLOUDINARY_STORAGE
    }