from django.urls import path
from django.shortcuts import redirect  # Add this line

from . import views

app_name = 'directory'

urlpatterns = [
    path('', views.coming_soon, name='home'),           # Public sees coming soon
    path('dev-home/', views.home, name='dev_home'),     # Developers access full site
    path('listings/', views.listings, name='listings'), # All filters work normally
    path('business/<int:pk>/', views.business_detail, name='business_detail'),
    path('business/<int:business_id>/add-review/', views.add_review, name='add_review'),
    path('business/<int:business_id>/send-enquiry/', views.send_enquiry, name='send_enquiry'),
    path('categories/', views.categories, name='categories'),
    path('api/search-suggestions/', views.search_suggestions, name='search_suggestions'),
    path('api/category-suggestions/', views.category_suggestions, name='category_suggestions'),
    path('api/pincode-suggestions/', views.pincode_suggestions, name='pincode_suggestions'),
    path('search-suggestions/', views.search_suggestions, name='search_suggestions'),
    path('add-listing/', views.add_listing, name='add_listing'),
    path('pincode-suggestions/', views.pincode_suggestions, name='pincode_suggestions'),
    
    # Dashboard URLs
    path('dashboard/', views.dashboard_home, name='dashboard_home'),
    path('dashboard/listings/', views.dashboard_listings, name='dashboard_listings'),
    path('dashboard/reviews/', views.dashboard_reviews, name='dashboard_reviews'),
    path('dashboard/enquiries/', views.dashboard_enquiries, name='dashboard_enquiries'),
    path('dashboard/enquiries/mark-responded/', views.mark_enquiry_responded, name='mark_enquiry_responded'),
    path('dashboard/reviews/approve/', views.approve_review, name='approve_review'),
    path('dashboard/listings/toggle-status/', views.toggle_business_status, name='toggle_business_status'),
    path('dashboard/leads/', views.dashboard_leads, name='dashboard_leads'),
    path('business/<int:business_id>/coupon/', views.request_coupon, name='request_coupon'),
    
    # KYC & GST Documents
    path('dashboard/kyc-gst/', views.kyc_gst_documents, name='kyc_gst_documents'),
    path('dashboard/monitor-redis/', views.monitor_redis, name='monitor_redis'),

    # Business addition and editing
    path('dashboard/business/start/', lambda request: redirect('directory:add_business'), name='add_business_start'),
    path('dashboard/business/add/', views.business_form, name='add_business'),
    path('dashboard/business/edit/<int:business_id>/', views.business_form, name='edit_business'),

    # Subscription URLs
    path('dashboard/subscription/', views.subscription_dashboard, name='subscription_dashboard'),
    path('plans/', views.subscription_plans, name='subscription_plans'),
    path('plans/select/<int:plan_id>/', views.select_plan, name='select_plan'),
    path('plans/payment/<int:subscription_id>/', views.payment_upload, name='payment_upload'),
    path('plans/success/', views.payment_success, name='payment_success'),

    # New Info Pages
    path('add-listings/', views.add_listings_info, name='add_listings_info'),
    path('refer-earn/', views.refer_earn, name='refer_earn'),

    # About Page
    path('about/', views.about, name='about'),

    # Legal pages
    path('terms/', views.terms, name='terms'),
    path('privacy/', views.privacy, name='privacy'),
    path('refund-policy/', views.refund_policy, name='refund_policy'),  # Add this line
    path('contact/', views.contact, name='contact'),  # Add this line

]