from django.urls import path
from . import views_profile

app_name = 'accounts'

urlpatterns = [
    # Profile and upgrade functionality
    path('profile/', views_profile.profile, name='profile'),
    path('upgrade-to-business/', views_profile.upgrade_to_business, name='upgrade_to_business'),
    path('password/change/', views_profile.password_change_redirect, name='password_change'),
]