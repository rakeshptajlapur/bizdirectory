from django.urls import path, include
from . import views

app_name = 'accounts'

urlpatterns = [
    # Profile and upgrade functionality
    path('profile/', views.profile, name='profile'),
    path('upgrade-to-business/', views.upgrade_to_business, name='upgrade_to_business'),
    path('password/change/', views.password_change_redirect, name='password_change'),
    # Add this for post-login redirect
    path('post-login/', views.post_login_redirect, name='post_login_redirect'),
    # Include allauth URLs
    path('', include('allauth.urls')),
]