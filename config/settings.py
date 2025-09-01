"""
Django settings for config project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv
import ssl

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env at project root
load_dotenv(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-9x5vlq=rqgfc)xe&g!6-#6x5e@5ii2t*-8&ea=r$7)ewbwxq_o')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Force HTTP for local development
if DEBUG:
    # Completely disable all HTTPS/SSL for local development
    SECURE_SSL_REDIRECT = False
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
    SECURE_CONTENT_TYPE_NOSNIFF = False
    SECURE_BROWSER_XSS_FILTER = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    USE_TLS = False
    
    # Force HTTP URLs
    ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'http'
    
    # Local CSRF trusted origins - HTTP only
    CSRF_TRUSTED_ORIGINS = [
        'http://127.0.0.1:8000',
        'http://localhost:8000',
    ]
    
    # Override any production settings
    ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'testserver']

# Improved ALLOWED_HOSTS handling
allowed_hosts_str = os.getenv('ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [host for host in allowed_hosts_str.split(',') if host.strip()]

# CSRF Trusted Origins - domains that can submit forms to your site
CSRF_TRUSTED_ORIGINS = []

if DEBUG:
    # Local development - HTTP only
    CSRF_TRUSTED_ORIGINS = [
        'http://127.0.0.1:8000',
        'http://localhost:8000',
    ]
else:
    # Production - HTTPS
    # Add all allowed hosts with https:// prefix to CSRF_TRUSTED_ORIGINS
    for host in ALLOWED_HOSTS:
        if host and not host.startswith('.') and not host.startswith('*'):
            CSRF_TRUSTED_ORIGINS.append(f'https://{host}')
        elif host and host.startswith('.'):
            CSRF_TRUSTED_ORIGINS.append(f'https://*{host}')
            CSRF_TRUSTED_ORIGINS.append(f'http://*{host}')

# Application definition
INSTALLED_APPS = [
    # ACCOUNTS MUST BE FIRST for template precedence
    'accounts',
    
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',  # Required for allauth
    
    # Allauth apps
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    
    # Other apps
    'directory',
    'affiliate',
    'widget_tweaks',
]

MIDDLEWARE = [
    # Comment out SecurityMiddleware for local development
    # 'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'debug': True,  # Enable template debugging
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
# Use PostgreSQL in production, SQLite in development
if os.getenv('DATABASE_URL'):
    # For production with DATABASE_URL
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.config(default=os.getenv('DATABASE_URL'))
    }
else:
    # For development
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'bizdirectory'),
            'USER': os.getenv('DB_USER', 'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
FILE_UPLOAD_PERMISSIONS = 0o644

# Security settings for file uploads
SECURE_FILE_UPLOAD = True

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Message tags for Bootstrap alert classes
from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.ERROR: 'danger',
    messages.WARNING: 'warning',
    messages.SUCCESS: 'success',
    messages.INFO: 'info',
}

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'  # FORCE SMTP
EMAIL_HOST = 'smtp.findnearbiz.com'  # Your actual SMTP server
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'support@findnearbiz.com')

# Allauth configuration
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'first_name', 'last_name', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_LOGIN_ON_PASSWORD_RESET = True
ACCOUNT_EMAIL_SUBJECT_PREFIX = 'BizDirectory - '

# Login/signup redirect URLs
LOGIN_REDIRECT_URL = '/dashboard/'
ACCOUNT_SIGNUP_REDIRECT_URL = '/accounts/confirm-email/'
ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL = '/accounts/login/'
ACCOUNT_LOGOUT_ON_GET = False

# Custom forms
ACCOUNT_FORMS = {
    'signup': 'accounts.forms.AllauthSignupForm',
}

# Custom URLs
ACCOUNT_LOGIN_URL = '/accounts/login/'
ACCOUNT_LOGOUT_URL = '/accounts/logout/'
ACCOUNT_SIGNUP_URL = '/accounts/signup/'

# Add these settings for allauth
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SITE_ID = 1  # Required for allauth

# Force template directories  
import os
TEMPLATES[0]['DIRS'] = [
    os.path.join(BASE_DIR, 'accounts', 'templates'),
]

# More verbose logging to debug email issues
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'accounts.adapter': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}

# Use Redis
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# For debug, allow long timeout
CELERY_TASK_SOFT_TIME_LIMIT = 300
CELERY_TASK_TIME_LIMIT = 600

# Media Files Configuration - Add this section
# Media files (user uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Use different storage backends for development and production
if not DEBUG:  # Production settings
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_ACCESS_KEY_ID = os.environ.get('R2_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('R2_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('R2_STORAGE_BUCKET_NAME', 'findnearbiz')
    AWS_S3_ENDPOINT_URL = f"https://{os.environ.get('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com"
    AWS_S3_CUSTOM_DOMAIN = os.environ.get('R2_CUSTOM_DOMAIN', f'{os.environ.get("R2_ACCOUNT_ID")}.r2.cloudflarestorage.com')
    AWS_LOCATION = 'media'
    AWS_S3_REGION_NAME = 'auto'  # R2 doesn't need a specific region
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_S3_ADDRESSING_STYLE = 'virtual'
    AWS_DEFAULT_ACL = 'public-read'
    AWS_QUERYSTRING_AUTH = False
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_LOCATION}/'
else:
    # Local development settings
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
    STATIC_URL = '/static/'
    STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
