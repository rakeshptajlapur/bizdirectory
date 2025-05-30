from django.urls import path
from . import views

app_name = 'directory'

urlpatterns = [
    path('', views.home, name='home'),
    path('business/<int:pk>/', views.business_detail, name='business_detail'),
    path('business/<int:business_id>/add-review/', views.add_review, name='add_review'),
    path('business/<int:business_id>/send-enquiry/', views.send_enquiry, name='send_enquiry'),
    path('categories/', views.categories, name='categories'),
    path('api/search-suggestions/', views.search_suggestions, name='search_suggestions'),
    path('api/category-suggestions/', views.category_suggestions, name='category_suggestions'),
    path('api/pincode-suggestions/', views.pincode_suggestions, name='pincode_suggestions'),
    path('listings/', views.listings, name='listings'),
    path('search-suggestions/', views.search_suggestions, name='search_suggestions'),
    path('add-listing/', views.add_listing, name='add_listing'),
    path('pincode-suggestions/', views.pincode_suggestions, name='pincode_suggestions'),
]