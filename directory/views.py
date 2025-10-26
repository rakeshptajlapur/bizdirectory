from django.shortcuts import render, get_object_or_404
from django.urls import reverse  # Add this line
from django.db.models import Q, Avg, Count
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.contrib.admin.views.decorators import staff_member_required
import redis
from django.conf import settings
from .forms import BusinessForm
from datetime import timedelta
import os
import logging
import math
from django.db.models import F, FloatField, ExpressionWrapper
from django.db.models.functions import Sin, Cos, Radians, Power, Sqrt, ATan2

# Fix missing imports
from .models import Business, Category, Service, BusinessImage, BusinessHours, Review, Enquiry, CouponRequest, SubscriptionPlan, UserSubscription

logger = logging.getLogger(__name__)

def home(request):
    search_query = request.GET.get('query', '')
    selected_category = request.GET.get('category', '')
    selected_pincode = request.GET.get('pincode', '')
    
    businesses = Business.objects.filter(is_active=True).prefetch_related('services')
    
    # Add this filter to only include approved reviews
    businesses = businesses.annotate(
        avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True)),
        approved_reviews_count=Count('reviews', filter=Q(reviews__is_approved=True))
    )
    
    if search_query:
        businesses = businesses.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    if selected_category:
        businesses = businesses.filter(category_id=selected_category)
    
    if selected_pincode:
        businesses = businesses.filter(pincode=selected_pincode)
    
    categories = Category.objects.all()
    
    # Get top categories with business counts
    top_categories = Category.objects.annotate(
        business_count=Count('business', filter=Q(business__is_active=True))
    ).order_by('-business_count')
    
    context = {
        'categories': categories,
        'top_categories': top_categories,
        'businesses': businesses[:10],  # Limit to 10 for homepage
        'search_query': search_query,
        'selected_category': selected_category,
        'selected_pincode': selected_pincode,
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY,  # ADD THIS LINE
    }
    
    return render(request, 'directory/home.html', context)

def business_detail(request, pk):
    """View for displaying a single business listing"""
    business = get_object_or_404(Business, pk=pk)
    
    # Get today's weekday (0=Monday, 6=Sunday)
    today_weekday = timezone.now().weekday()
    
    # Convert to 1-7 range to match our model's DAYS_OF_WEEK values
    today_weekday_adjusted = today_weekday + 1
    
    # Get today's hours using ONLY the adjusted value
    today_hours = business.hours.filter(day=today_weekday_adjusted).first()
    
    # Calculate average rating from approved reviews
    business.avg_rating = business.reviews.filter(is_approved=True).aggregate(
        avg=Avg('rating')
    )['avg'] or 0
    
    # Count only approved reviews
    business.approved_reviews_count = business.reviews.filter(is_approved=True).count()
    
    # Check if visitor has already submitted a review
    user_review = None
    reviewer_email = request.session.get('reviewer_email')
    if reviewer_email:
        user_review = business.reviews.filter(email=reviewer_email).first()
    
    # Get related businesses in same category (excluding current business)
    related_businesses = Business.objects.filter(
        category=business.category
    ).exclude(
        pk=business.pk
    ).annotate(
        avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True))
    ).order_by('-avg_rating')[:3]  # Top 3 rated related businesses
    
    context = {
        'business': business,
        'today_weekday': today_weekday_adjusted,  # Use adjusted value in template
        'today_hours': today_hours,
        'related_businesses': related_businesses,
        'user_review': user_review,
    }
    return render(request, 'directory/business_detail.html', context)

def search_suggestions(request):
    """AJAX endpoint for search suggestions"""
    term = request.GET.get('term', '')
    suggestion_type = request.GET.get('type', 'search')
    
    if suggestion_type == 'categories':
        # Return all categories with business count
        from django.db.models import Count
        categories = Category.objects.annotate(
            business_count=Count('business', filter=Q(business__is_active=True))
        ).filter(business_count__gt=0).order_by('name')
        
        suggestions = [
            {
                'id': category.id,
                'name': category.name,
                'business_count': category.business_count
            }
            for category in categories
        ]
    else:
        # Existing search suggestions logic
        businesses = Business.objects.filter(
            Q(name__icontains=term) | Q(description__icontains=term),
            is_active=True
        )[:10]
        
        suggestions = [
            {'label': business.name, 'value': business.name}
            for business in businesses
        ]
    
    return JsonResponse(suggestions, safe=False)

def location_suggestions(request):
    """Enhanced location suggestions for location search"""
    term = request.GET.get('term', '')
    
    if not term or len(term) < 2:
        return JsonResponse([], safe=False)
    
    suggestions = []
    
    # Get unique cities with business count
    cities = Business.objects.filter(
        Q(city__icontains=term) & Q(is_active=True)
    ).values('city').annotate(
        business_count=Count('id')
    ).order_by('-business_count', 'city')[:5]
    
    for city in cities:
        suggestions.append(f"{city['city']} ({city['business_count']} businesses)")
    
    # Get popular areas/localities from addresses
    areas = Business.objects.filter(
        Q(address__icontains=term) & Q(is_active=True)
    ).exclude(
        city__icontains=term  # Don't duplicate cities
    ).values_list('address', flat=True)[:3]
    
    # Extract area names from addresses (simple extraction)
    for address in areas:
        # Try to extract area name (words that contain the search term)
        words = address.split(',')
        for word in words:
            word = word.strip()
            if term.lower() in word.lower() and len(word) > len(term):
                suggestions.append(word[:50])  # Limit length
                break
    
    # Get states if searching for state names
    if len(term) >= 3:
        states = Business.objects.filter(
            Q(state__icontains=term) & Q(is_active=True)
        ).values('state').annotate(
            business_count=Count('id')
        ).order_by('-business_count', 'state')[:2]
        
        for state in states:
            suggestions.append(f"{state['state']} State ({state['business_count']} businesses)")
    
    # Remove duplicates while preserving order
    unique_suggestions = list(dict.fromkeys(suggestions))[:8]
    
    return JsonResponse(unique_suggestions, safe=False)

def category_suggestions(request):
    categories = Category.objects.all().values('id', 'name')
    return JsonResponse(list(categories), safe=False)

def pincode_suggestions(request):
    query = request.GET.get('term', '')
    if not query:
        return JsonResponse([], safe=False)
    
    # Get unique pincodes that match the query
    pincodes = Business.objects.filter(
        pincode__startswith=query  # Fixed: using = instead of parentheses
    ).values_list('pincode', flat=True).distinct()[:10]
    
    return JsonResponse(list(pincodes), safe=False)

# Add this view function
def categories(request):
    """View for browsing all categories"""
    categories = Category.objects.all().order_by('name')
    
    # Create a dictionary organized by first letter
    categorized = {}
    total_businesses = 0
    
    for category in categories:
        first_letter = category.name[0].upper()
        if first_letter not in categorized:
            categorized[first_letter] = []
        categorized[first_letter].append(category)
    
    # Count businesses in each category
    for letter in categorized:
        for category in categorized[letter]:
            category.business_count = Business.objects.filter(category=category, is_active=True).count()
            total_businesses += category.business_count
    
    return render(request, 'directory/categories.html', {
        'categorized': categorized,
        'total_businesses': total_businesses
    })

def listings(request):
    """View for all business listings with filters"""
    
    # Base queryset with optimized queries
    businesses = Business.objects.filter(is_active=True).select_related('category', 'owner').prefetch_related('services', 'reviews')
    
    # Add this annotation to calculate approved reviews count
    businesses = businesses.annotate(
        avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True)),
        approved_reviews_count=Count('reviews', filter=Q(reviews__is_approved=True))
    ).order_by('-created_at')
    
    # Apply filters
    category_ids = request.GET.get('category')
    if category_ids:
        try:
            # Handle multiple categories separated by commas
            if ',' in category_ids:
                category_list = [int(cat_id.strip()) for cat_id in category_ids.split(',') if cat_id.strip()]
                businesses = businesses.filter(category_id__in=category_list)
            else:
                # Single category
                businesses = businesses.filter(category_id=int(category_ids))
        except (ValueError, TypeError):
            # Invalid category ID, ignore the filter
            pass
    
    # UPDATED: Rating filter for exact rating match
    rating = request.GET.get('rating')
    if rating:
        try:
            rating_int = int(rating)
            businesses = businesses.filter(
                avg_rating__gte=rating_int - 0.5,
                avg_rating__lt=rating_int + 0.5
            )
        except ValueError:
            pass
    
    # NEW: Geographic Location Search with Radius
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    radius = request.GET.get('radius', 50)  # Default 50km radius
    location_query = request.GET.get('location')
    
    if lat and lng:
        # Convert to float
        try:
            user_lat = float(lat)
            user_lng = float(lng)
            search_radius = float(radius)
            
            # Haversine formula for distance calculation
            businesses = businesses.filter(
                latitude__isnull=False,
                longitude__isnull=False
            ).annotate(
                distance_km=ExpressionWrapper(
                    6371 * 2 * ATan2(
                        Sqrt(
                            Sin(Radians(F('latitude') - user_lat) / 2) ** 2 +
                            Cos(Radians(user_lat)) * Cos(Radians(F('latitude'))) *
                            Sin(Radians(F('longitude') - user_lng) / 2) ** 2
                        ),
                        Sqrt(1 - (
                            Sin(Radians(F('latitude') - user_lat) / 2) ** 2 +
                            Cos(Radians(user_lat)) * Cos(Radians(F('latitude'))) *
                            Sin(Radians(F('longitude') - user_lng) / 2) ** 2
                        ))
                    ),
                    output_field=FloatField()
                )
            ).filter(
                distance_km__lte=search_radius
            ).order_by('distance_km', '-created_at')  # Order by distance first
            
            print(f"Geographic search: {businesses.count()} businesses found within {radius}km of ({lat}, {lng})")
            
        except (ValueError, TypeError):
            print("Invalid coordinates provided")
    
    elif location_query:
        # Fallback: Text-based location search (as backup)
        location_query = location_query.strip()
        
        # Search in multiple location fields for broader matching
        location_filter = Q()
        
        # Split location query into words for better matching
        location_words = location_query.split()
        
        for word in location_words:
            if len(word) >= 2:  # Only search words with 2+ characters
                location_filter |= (
                    Q(city__icontains=word) |
                    Q(address__icontains=word) |
                    Q(formatted_address__icontains=word) |
                    Q(pincode__icontains=word) |
                    Q(state__icontains=word)
                )
        
        # If no words found, search the whole query
        if not location_words:
            location_filter = (
                Q(city__icontains=location_query) |
                Q(address__icontains=location_query) |
                Q(formatted_address__icontains=location_query) |
                Q(pincode__icontains=location_query) |
                Q(state__icontains=location_query)
            )
        
        businesses = businesses.filter(location_filter).distinct()
        print(f"Text-based location search: {businesses.count()} businesses found for '{location_query}'")
    
    # Rest of your existing filters...
    pincode = request.GET.get('pincode')
    if pincode:
        businesses = businesses.filter(pincode__startswith=pincode)
    
    trust_filter = request.GET.get('trust')
    if trust_filter == 'gst':
        businesses = businesses.filter(gst_verified=True)
    elif trust_filter == 'kyc':
        businesses = businesses.filter(kyc_status='completed')
    elif trust_filter == 'both':
        businesses = businesses.filter(gst_verified=True, kyc_status='completed')
    
    search_query = request.GET.get('query')
    if search_query:
        businesses = businesses.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query) |
            Q(services__name__icontains=search_query)
        ).distinct()
    
    # Get all categories for the filter sidebar
    categories = Category.objects.all()
    
    # ADDED: Calculate rating counts for dropdown
    from django.db.models import Case, When, IntegerField
    
    rating_counts = {}
    for i in range(1, 6):
        count = Business.objects.filter(is_active=True).annotate(
            avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True))
        ).filter(
            avg_rating__gte=i - 0.5,
            avg_rating__lt=i + 0.5
        ).count()
        rating_counts[i] = count
    
    # Pagination
    paginator = Paginator(businesses, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Prepare current filters for maintaining state
    current_filters = {}
    for param in ['category', 'rating', 'verification', 'query', 'location', 'lat', 'lng', 'radius']:
        if request.GET.get(param):
            current_filters[param] = request.GET.get(param)
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'current_filters': current_filters,
        'rating_counts': rating_counts,  # ADDED: Rating counts for dropdown
    }
    
    return render(request, 'directory/listings.html', context)

# In your directory/views.py
def add_listing(request):
    """View for the add listing page"""
    return render(request, 'directory/add_listing.html')

def add_review(request, business_id):
    """Handle review submission for authenticated users"""
    business = get_object_or_404(Business, pk=business_id)
    
    # Ensure user is authenticated (since review form is only shown to auth users)
    if not request.user.is_authenticated:
        messages.error(request, "Please login to submit a review.")
        return redirect('account_login')
    
    if request.method == 'POST':
        # Get form data - use authenticated user's data
        name = request.user.get_full_name() or request.user.username
        email = request.user.email
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        # Validate input
        if not rating:
            messages.error(request, "Please select a rating")
            return redirect('directory:business_detail', pk=business_id)
            
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                messages.error(request, "Rating must be between 1 and 5")
                return redirect('directory:business_detail', pk=business_id)
        except (ValueError, TypeError):
            messages.error(request, "Invalid rating value")
            return redirect('directory:business_detail', pk=business_id)
            
        if not comment or len(comment.strip()) < 10:
            messages.error(request, "Please provide a review comment (minimum 10 characters)")
            return redirect('directory:business_detail', pk=business_id)
        
        # Check if user has already reviewed this business
        existing_review = Review.objects.filter(
            business=business, 
            user=request.user  # Use user field instead of email
        ).first()
        
        if existing_review:
            # Update existing review
            existing_review.name = name
            existing_review.email = email
            existing_review.rating = rating
            existing_review.comment = comment.strip()
            existing_review.is_approved = False  # Reset approval on update
            existing_review.save()
            messages.success(request, "Your review has been updated and is pending approval.")
        else:
            # Create new review
            Review.objects.create(
                business=business,
                user=request.user,  # Link to authenticated user
                name=name,
                email=email,
                rating=rating,
                comment=comment.strip(),
                is_approved=False
            )
            messages.success(request, "Thank you! Your review has been submitted and is pending approval.")
        
        return redirect('directory:business_detail', pk=business_id)
    
    # GET requests redirect back to business detail
    return redirect('directory:business_detail', pk=business_id)

def send_enquiry(request, business_id):
    """Handle enquiry form submissions for authenticated users"""
    business = get_object_or_404(Business, pk=business_id)
    
    # Ensure user is authenticated
    if not request.user.is_authenticated:
        messages.error(request, "Please login to send an enquiry.")
        return redirect('account_login')
    
    if request.method == 'POST':
        # Get form data - use authenticated user's data for name, email, phone
        name = request.user.get_full_name() or request.user.username
        email = request.user.email
        phone = getattr(request.user.profile, 'phone', '') if hasattr(request.user, 'profile') else ''
        message = request.POST.get('message', '').strip()
        
        # Validate input
        if not message:
            messages.error(request, "Please provide your message")
            return redirect('directory:business_detail', pk=business_id)
            
        if len(message) < 10:
            messages.error(request, "Message should be at least 10 characters long")
            return redirect('directory:business_detail', pk=business_id)
        
        # Create new enquiry
        Enquiry.objects.create(
            business=business,
            name=name,
            email=email,
            phone=phone,
            message=message
        )
        
        messages.success(request, "Thank you! Your enquiry has been sent to the business owner.")
        return redirect('directory:business_detail', pk=business_id)
    
    # GET requests redirect back to business detail
    return redirect('directory:business_detail', pk=business_id)

def request_coupon(request, business_id):
    """Handle coupon form submissions for authenticated users"""
    business = get_object_or_404(Business, pk=business_id)
    
    if not request.user.is_authenticated:
        messages.error(request, "Please login to request a coupon.")
        return redirect('account_login')
    
    # Check if coupons are enabled for this business
    if not business.coupon_enabled:
        messages.error(request, "Coupons are currently not available for this business.")
        return redirect('directory:business_detail', pk=business_id)
    
    if request.method == 'POST':
        email = request.user.email
        
        try:
            existing_coupon = CouponRequest.objects.filter(business=business, email=email).first()
            if existing_coupon:
                messages.info(request, f"You've already requested a coupon. Your code is: {existing_coupon.coupon_code}")
            else:
                import random
                import string
                code_chars = string.ascii_uppercase + string.digits
                coupon_code = ''.join(random.choice(code_chars) for _ in range(8))
                
                CouponRequest.objects.create(
                    business=business,
                    email=email,
                    coupon_code=coupon_code,
                    discount_percentage=business.coupon_discount,
                    is_sent=True
                )
                messages.success(request, f"Success! Your {business.coupon_discount}% discount code is: {coupon_code}")
                
        except Exception as e:
            messages.error(request, "Sorry, something went wrong. Please try again later.")
        
    return redirect('directory:business_detail', pk=business_id)

@login_required
def dashboard_home(request):
    """Dashboard home view with 3-box layout"""
    # Get businesses owned by the current user (if they're a business owner)
    businesses = Business.objects.filter(owner=request.user) if hasattr(request.user, 'profile') and request.user.profile.is_business_owner else Business.objects.none()
    
    # Initialize stats
    premium_listings_count = 0
    enquiries_count = 0
    coupon_requests_count = 0
    reviews_count = 0
    total_leads_count = 0
    avg_rating = 0
    unread_enquiries = 0
    pending_reviews = 0
    recent_enquiries = []
    recent_reviews = []
    
    # Only calculate stats for business owners
    if hasattr(request.user, 'profile') and request.user.profile.is_business_owner:
        # Count premium listings using the existing property
        premium_listings_count = sum(1 for business in businesses if business.has_premium_features)
        
        # Get all lead sources
        enquiries_count = Enquiry.objects.filter(business__owner=request.user).count()
        reviews_count = Review.objects.filter(business__owner=request.user).count()
        
        # Count coupon requests (if you have this functionality)
        coupon_requests_count = 0  # Set this based on your actual coupon model if it exists
        
        # Total leads = enquiries + coupon requests + reviews
        total_leads_count = enquiries_count + coupon_requests_count + reviews_count
        
        # Calculate average rating across all businesses
        from django.db.models import Avg
        avg_rating = Review.objects.filter(
            business__owner=request.user,
            is_approved=True  # Only count approved reviews
        ).aggregate(Avg('rating'))['rating__avg'] or 0
        
        # Get unread enquiries and pending reviews counts for notifications
        unread_enquiries = Enquiry.objects.filter(business__owner=request.user, is_responded=False).count()
        pending_reviews = Review.objects.filter(business__owner=request.user, is_approved=False).count()
        
        # Get recent enquiries and reviews
        recent_enquiries = Enquiry.objects.filter(
            business__owner=request.user
        ).order_by('-created_at')[:5]
        
        recent_reviews = Review.objects.filter(
            business__owner=request.user
        ).order_by('-created_at')[:5]

    context = {
        'active_tab': 'home',
        'businesses': businesses,
        'premium_listings_count': premium_listings_count,
        'enquiries_count': enquiries_count,
        'coupon_requests_count': coupon_requests_count,
        'reviews_count': reviews_count,
        'total_leads_count': total_leads_count,
        'avg_rating': avg_rating,
        'recent_enquiries': recent_enquiries,
        'recent_reviews': recent_reviews,
        'unread_enquiries_count': unread_enquiries,
        'pending_reviews_count': pending_reviews,
    }
    
    return render(request, 'directory/dashboard/home.html', context)

@login_required
def dashboard_listings(request):
    """Dashboard listings view"""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_business_owner:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('directory:home')
    
    businesses = Business.objects.filter(owner=request.user)
    
    context = {
        'active_tab': 'listings',
        'businesses': businesses,
    }
    
    return render(request, 'directory/dashboard/listings.html', context)

@login_required
def dashboard_reviews(request):
    """Dashboard reviews view"""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_business_owner:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('directory:home')
    
    reviews = Review.objects.filter(business__owner=request.user).order_by('-created_at')
    
    context = {
        'active_tab': 'reviews',
        'reviews': reviews,
    }
    
    return render(request, 'directory/dashboard/reviews.html', context)

@login_required
def dashboard_enquiries(request):
    """Dashboard enquiries view"""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_business_owner:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('directory:home')
    
    enquiries = Enquiry.objects.filter(business__owner=request.user).order_by('-created_at')
    
    context = {
        'active_tab': 'enquiries',
        'enquiries': enquiries,
    }
    
    return render(request, 'directory/dashboard/enquiries.html', context)

@login_required
def mark_enquiry_responded(request):
    """Mark an enquiry as responded"""
    if request.method == 'POST':
        enquiry_id = request.POST.get('enquiry_id')
        enquiry = get_object_or_404(Enquiry, id=enquiry_id, business__owner=request.user)
        
        enquiry.is_responded = True
        enquiry.save()
        
        messages.success(request, "Enquiry marked as responded.")
    
    return redirect('directory:dashboard_enquiries')

@login_required
def approve_review(request):
    """Approve a review"""
    if request.method == 'POST':
        review_id = request.POST.get('review_id')
        review = get_object_or_404(Review, id=review_id, business__owner=request.user)
        
        review.is_approved = True
        review.save()
        
        messages.success(request, "Review approved and now visible to all users.")
    
    return redirect('directory:dashboard_reviews')

@login_required
def toggle_business_status(request):
    """Toggle the active status of a business"""
    if request.method == 'POST':
        business_id = request.POST.get('business_id')
        business = get_object_or_404(Business, id=business_id, owner=request.user)
        
        business.is_active = not business.is_active
        business.save()
        
        status = "activated" if business.is_active else "deactivated"
        messages.success(request, f"Business {business.name} has been {status}.")
    
    return redirect('directory:dashboard_listings')

@login_required
def dashboard_leads(request):
    """Dashboard leads view - consolidated view of all leads"""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_business_owner:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('directory:home')
    
    # Get all leads data
    enquiries = Enquiry.objects.filter(business__owner=request.user).order_by('-created_at')
    reviews = Review.objects.filter(business__owner=request.user).order_by('-created_at')
    
    # Get coupon requests if the model exists
    coupon_requests = []
    try:
        from .models import CouponRequest
        coupon_requests = CouponRequest.objects.filter(business__owner=request.user).order_by('-created_at')
    except (ImportError, AttributeError):
        pass
    
    # Statistics
    enquiries_count = enquiries.count()
    reviews_count = reviews.count()
    coupon_requests_count = len(coupon_requests)
    unread_enquiries_count = enquiries.filter(is_responded=False).count()
    pending_reviews_count = reviews.filter(is_approved=False).count()
    
    context = {
        'active_tab': 'leads',
        'enquiries': enquiries[:50],  # Limit to recent 50
        'reviews': reviews[:50],
        'coupon_requests': coupon_requests[:50] if coupon_requests else [],
        'enquiries_count': enquiries_count,
        'reviews_count': reviews_count,
        'coupon_requests_count': coupon_requests_count,
        'unread_enquiries_count': unread_enquiries_count,
        'pending_reviews_count': pending_reviews_count,
    }
    
    return render(request, 'directory/dashboard/leads.html', context)

@login_required
def kyc_gst_documents(request):
    """KYC & GST documents overview"""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_business_owner:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('directory:home')
    
    # Get all businesses owned by this user
    businesses = Business.objects.filter(owner=request.user)
    
    if not businesses.exists():
        messages.error(request, "Please create a business listing first.")
        return redirect('directory:dashboard_home')
    
    context = {
        'active_tab': 'kyc_gst',
        'businesses': businesses,
    }
    return render(request, 'directory/dashboard/kyc_gst.html', context)

@login_required
def business_form(request, business_id=None):
    """Add new business or edit existing business"""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_business_owner:
        messages.error(request, "You need to upgrade to a business owner account first.")
        return redirect('accounts:upgrade_to_business')
    
    # Initialize variables
    business = None
    is_edit = False
    
    # Determine if editing or adding
    if business_id:
        business = get_object_or_404(Business, id=business_id, owner=request.user)
        is_edit = True
    
    # Process form submission
    if request.method == 'POST':
        form = BusinessForm(request.POST, request.FILES, instance=business, user=request.user)
        
        if form.is_valid():
            business = form.save(commit=False)
            
            # ✅ Handle location data from Google Maps FIRST - ENHANCED
            business.latitude = request.POST.get('latitude') or None
            business.longitude = request.POST.get('longitude') or None
            business.place_id = request.POST.get('place_id', '')
            
            # Fix location name storage - use business name if location_name is empty
            location_name = request.POST.get('location_name', '')
            if not location_name and business.name:
                location_name = business.name  # Fallback to business name
            business.location_name = location_name
            
            business.formatted_address = request.POST.get('formatted_address', '')
            
            # ✅ Auto-populated location fields
            business.address = request.POST.get('formatted_address', '') or business.address
            business.city = request.POST.get('city', '') or business.city
            business.pincode = request.POST.get('pincode', '') or business.pincode
            business.state = request.POST.get('state', '') or business.state
            
            # ✅ Enhanced debug logging
            print(f"Location data being saved:")
            print(f"  Business Name: {business.name}")
            print(f"  Location Name: {business.location_name}")
            print(f"  Formatted Address: {business.formatted_address}")
            print(f"  Latitude: {business.latitude}")
            print(f"  Longitude: {business.longitude}")
            print(f"  City: {business.city}")
            print(f"  State: {business.state}")
            print(f"  Pincode: {business.pincode}")
            
            if not is_edit:
                business.owner = request.user
                # Auto-assign free plan for new businesses
                free_plan = SubscriptionPlan.objects.filter(price=0).first()
                business.subscription_plan = free_plan
                business.save()
                
                # Create an active subscription record for the free plan
                UserSubscription.objects.create(
                    user=request.user,
                    business=business,
                    plan=free_plan,
                    is_active=True,
                    payment_status='verified',
                    expiry_date=timezone.now() + timedelta(days=free_plan.duration_days)
                )
            
            # Handle action (draft vs submit)
            action = request.POST.get('action', 'draft')
            if action == 'draft':
                business.is_active = False
                business.kyc_status = 'not_submitted'
                status_message = 'Business listing saved as draft successfully!'
            else:  # submit
                business.is_active = True
                business.kyc_status = 'pending'
                status_message = 'Business listing submitted for approval successfully!'
            
            business.save()  # ✅ This will now save location data too
            
            # Add logging for primary image
            primary_image = request.FILES.get('primary_image')
            if primary_image:
                logger.info(f"Primary image upload: business={business.id}, file={primary_image.name}, size={primary_image.size}B, type={primary_image.content_type}")
                try:
                    # Remove existing primary image
                    BusinessImage.objects.filter(business=business, is_primary=True).delete()
                    # Add new primary image
                    BusinessImage.objects.create(
                        business=business,
                        image=primary_image,
                        is_primary=True,
                        caption=f"{business.name} - Main Image"
                    )
                    logger.info(f"Primary image saved successfully: business={business.id}")
                except Exception as e:
                    logger.error(f"Primary image save failed: business={business.id}, error={str(e)}", exc_info=True)
            
            # Add logging for gallery images
            gallery_images = request.FILES.getlist('gallery_images')
            for i, img in enumerate(gallery_images):
                logger.info(f"Gallery image upload #{i+1}: business={business.id}, file={img.name}, size={img.size}B, type={img.content_type}")
                try:
                    BusinessImage.objects.create(
                        business=business,
                        image=img,
                        is_primary=False,
                        caption=f"{business.name} - Gallery Image"
                    )
                    logger.info(f"Gallery image #{i+1} saved successfully: business={business.id}")
                except Exception as e:
                    logger.error(f"Gallery image #{i+1} save failed: business={business.id}, error={str(e)}", exc_info=True)
            
            # Update with user feedback
            # Handle registration document with validation
            registration_document = request.FILES.get('registration_document')
            if registration_document:
                logger.info(f"Registration document upload: business={business.id}, file={registration_document.name}, size={registration_document.size}B, type={registration_document.content_type}")
                try:
                    # Validate the document
                    form.validate_document_file(registration_document)
                    
                    business.registration_document = registration_document
                    business.kyc_status = 'pending'  # Set KYC status to pending when new document uploaded
                    business.save()  # Save immediately to ensure the file is saved
                    logger.info(f"Registration document saved successfully: business={business.id}")
                    messages.success(request, "Registration certificate uploaded successfully. KYC verification is in progress.")
                except ValidationError as e:
                    logger.error(f"Registration document validation failed: business={business.id}, error={str(e)}")
                    messages.error(request, f"Registration document upload failed: {str(e)}")
                except Exception as e:
                    logger.error(f"Registration document save failed: business={business.id}, error={str(e)}", exc_info=True)
                    messages.error(request, "Failed to upload registration certificate. Please try again.")

            # Handle GST document with validation
            gst_document = request.FILES.get('gst_document')
            if gst_document:
                logger.info(f"GST document upload: business={business.id}, file={gst_document.name}, size={gst_document.size}B, type={gst_document.content_type}")
                try:
                    # Validate the document
                    form.validate_document_file(gst_document)
                    
                    business.gst_document = gst_document
                    if business.gst_number:
                        business.gst_verified = False  # Reset verification status when new document uploaded
                    business.save()  # Save immediately to ensure the file is saved
                    logger.info(f"GST document saved successfully: business={business.id}")
                    messages.success(request, "GST certificate uploaded successfully and will be verified shortly.")
                except ValidationError as e:
                    logger.error(f"GST document validation failed: business={business.id}, error={str(e)}")
                    messages.error(request, f"GST document upload failed: {str(e)}")
                except Exception as e:
                    logger.error(f"GST document save failed: business={business.id}, error={str(e)}", exc_info=True)
                    messages.error(request, "Failed to upload GST certificate. Please try again.")
            
            # Handle business hours
            days_of_week = range(1, 8)  # 1-7 (Monday to Sunday)
            for day in days_of_week:
                is_closed = request.POST.get(f'closed_{day}') == 'on'
                open_time = request.POST.get(f'open_time_{day}', '')
                close_time = request.POST.get(f'close_time_{day}', '')
                
                # Find existing hours or create new
                hours, created = BusinessHours.objects.get_or_create(
                    business=business,
                    day=day,
                    defaults={
                        'is_closed': True,
                        'open_time': '09:00',
                        'close_time': '17:00'
                    }
                )
                
                # Update the hours
                hours.is_closed = is_closed
                if not is_closed and open_time and close_time:
                    hours.open_time = open_time
                    hours.close_time = close_time
                hours.save()
            
            # Handle services
            service_names = request.POST.getlist('service_name')
            service_descriptions = request.POST.getlist('service_description')
            
            # Delete existing services for this business
            Service.objects.filter(business=business).delete()
            
            # Create new services
            for i, name in enumerate(service_names):
                if name.strip():  # Only process non-empty service names
                    description = service_descriptions[i] if i < len(service_descriptions) else ""
                    Service.objects.create(
                        business=business,
                        name=name.strip(),
                        description=description.strip()
                    )
            
            # Link subscription to business if adding new business
            if not is_edit and 'pending_subscription_id' in request.session:
                subscription_id = request.session.get('pending_subscription_id')
                subscription = UserSubscription.objects.get(id=subscription_id)
                subscription.business = business
                subscription.save()
                # Clear the session
                del request.session['pending_subscription_id']
            
            messages.success(request, status_message)
            return redirect('directory:dashboard_listings')
    else:
        # Initialize an empty form for GET requests - THIS WAS MISSING
        form = BusinessForm(instance=business, user=request.user)
    
    # Get business hours for the form
    business_hours = {}
    if business:
        for hours in business.hours.all():
            business_hours[hours.day] = {
                'is_closed': hours.is_closed,
                'open_time': hours.open_time,
                'close_time': hours.close_time
            }
    
    # Get services for the form
    services = []
    if business:
        services = list(business.services.all().values('name', 'description'))
    
    # Get gallery images
    gallery_images = []
    if business:
        gallery_images = business.images.filter(is_primary=False)
    
    context = {
        'active_tab': 'add_business' if not is_edit else 'listings',
        'form': form,
        'business': business,
        'business_hours': business_hours,
        'services': services,
        'gallery_images': gallery_images,
        'is_edit': is_edit,
        'days_of_week': [
            {'number': 1, 'name': 'Monday'},
            {'number': 2, 'name': 'Tuesday'},
            {'number': 3, 'name': 'Wednesday'},
            {'number': 4, 'name': 'Thursday'},
            {'number': 5, 'name': 'Friday'},
            {'number': 6, 'name': 'Saturday'},
            {'number': 7, 'name': 'Sunday'}
        ]
    }
    return render(request, 'directory/dashboard/business_form.html', context)

# Add these view functions

@login_required
def subscription_plans(request):
    """View to select subscription plans"""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_business_owner:
        messages.error(request, "Only business owners can subscribe to plans.")
        return redirect('accounts:upgrade_to_business')
    
    # Get available subscription plans
    plans = SubscriptionPlan.objects.all()
    
    # Check if this is for a new business or an existing one
    for_new_business = request.GET.get('for_new_business') == 'true'
    for_business_id = request.GET.get('for_business')
    business = None
    
    if for_business_id:
        business = get_object_or_404(Business, id=for_business_id, owner=request.user)
    
    context = {
        'plans': plans,
        'for_new_business': for_new_business,
        'business': business
    }
    
    return render(request, 'directory/subscription/plans.html', context)

@login_required
def select_plan(request, plan_id):
    """Handle plan selection"""
    # Permission check
    if not hasattr(request.user, 'profile') or not request.user.profile.is_business_owner:
        messages.error(request, "Only business owners can subscribe to plans.")
        return redirect('accounts:upgrade_to_business')
    
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)
    
    # Check if this is for a new or existing business
    for_new_business = request.GET.get('for_new_business') == 'true'
    for_business_id = request.GET.get('for_business')
    business = None
    
    if for_business_id:
        business = get_object_or_404(Business, id=for_business_id, owner=request.user)
        
        # Check if the business already has a subscription
        try:
            existing_subscription = UserSubscription.objects.get(business=business)
            
            # If upgrading to the same plan, just redirect back
            if existing_subscription.plan == plan:
                messages.info(request, f"This business is already on the {plan.name} plan.")
                return redirect('directory:dashboard_listings')
                
            # For existing subscriptions, just update the plan instead of creating a new one
            existing_subscription.plan = plan
            existing_subscription.expiry_date = timezone.now() + timedelta(days=plan.duration_days)
            existing_subscription.payment_status = 'pending'  # Reset payment status for paid upgrades
            existing_subscription.is_active = False if plan.price > 0 else True  # Only auto-activate free plans
            existing_subscription.save()
            
            # If free plan, activate immediately
            if plan.price == 0:
                existing_subscription.is_active = True
                existing_subscription.payment_status = 'verified'
                existing_subscription.save()
                
                messages.success(request, f"Your subscription has been updated to {plan.name}.")
                return redirect('directory:dashboard_listings')
            
            # For paid plans, redirect to payment
            return redirect('directory:payment_upload', subscription_id=existing_subscription.id)
            
        except UserSubscription.DoesNotExist:
            # No existing subscription, so we'll create a new one
            pass
    
    # Create a new subscription for new businesses or businesses without a subscription
    subscription = UserSubscription.objects.create(
        user=request.user,
        business=business,
        plan=plan,
        expiry_date=timezone.now() + timedelta(days=plan.duration_days)
    )
    
    # If free plan, activate immediately
    if plan.price == 0:
        subscription.is_active = True
        subscription.payment_status = 'verified'
        subscription.save()
        
        if business:
            messages.success(request, f"Your {business.name} subscription has been updated to {plan.name}.")
            return redirect('directory:dashboard_listings')
        else:
            request.session['pending_subscription_id'] = subscription.id
            messages.success(request, f"You've selected the {plan.name} plan. Now add your business details.")
            return redirect('directory:add_business')
    
    # For paid plans, redirect to payment
    return redirect(f"{reverse('directory:payment_upload', args=[subscription.id])}?for_new_business={for_new_business}&for_business_id={for_business_id or ''}")

@login_required
def payment_upload(request, subscription_id):
    """Handle payment screenshot upload"""
    subscription = get_object_or_404(UserSubscription, id=subscription_id, user=request.user)
    
    if request.method == 'POST':
        payment_screenshot = request.FILES.get('payment_screenshot')
        
        # Add affiliate code handling
        affiliate_code = request.POST.get('affiliate_code')
        if affiliate_code:
            # Check if valid affiliate code
            from affiliate.models import AffiliateProfile
            try:
                affiliate = AffiliateProfile.objects.get(affiliate_code=affiliate_code, status='approved')
                subscription.affiliate_code = affiliate_code
                subscription.save()
            except AffiliateProfile.DoesNotExist:
                messages.warning(request, "Invalid affiliate code, but your payment is still being processed.")
        
        if payment_screenshot:
            # ✅ Add file validation
            try:
                # Validate file size (5MB max)
                max_size = 5 * 1024 * 1024  # 5MB
                if payment_screenshot.size > max_size:
                    messages.error(request, "File size should not exceed 5MB.")
                    return render(request, 'directory/subscription/payment.html', {
                        'subscription': subscription,
                        'for_new_business': request.GET.get('for_new_business') == 'true',
                        'for_business_id': request.GET.get('for_business_id'),
                    })
                
                # Validate file type
                allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf']
                if hasattr(payment_screenshot, 'content_type') and payment_screenshot.content_type not in allowed_types:
                    messages.error(request, "File must be a JPG, PNG image or PDF document.")
                    return render(request, 'directory/subscription/payment.html', {
                        'subscription': subscription,
                        'for_new_business': request.GET.get('for_new_business') == 'true',
                        'for_business_id': request.GET.get('for_business_id'),
                    })
                
                # Save the file
                subscription.payment_screenshot = payment_screenshot
                subscription.payment_status = 'pending'
                subscription.save()
                
                file_type = "PDF" if payment_screenshot.content_type == 'application/pdf' else "image"
                messages.success(request, f"Payment {file_type} uploaded successfully. Your subscription will be activated after verification.")
                return redirect('directory:payment_success')
                
            except Exception as e:
                logger.error(f"Payment screenshot upload error: {e}")
                messages.error(request, "Failed to upload payment receipt. Please try again.")
        else:
            messages.error(request, "Please upload a payment receipt.")
    
    # Get query parameters
    for_new_business = request.GET.get('for_new_business') == 'true'
    for_business_id = request.GET.get('for_business_id')
    
    context = {
        'subscription': subscription,
        'for_new_business': for_new_business,
        'for_business_id': for_business_id,
        'upi_id': 'yourbusiness@upi'  # Replace with your actual UPI ID
    }
    
    return render(request, 'directory/subscription/payment.html', context)

@login_required
def payment_success(request):
    """Payment success page"""
    return render(request, 'directory/subscription/success.html')

@login_required
def subscription_dashboard(request):
    """User's subscription dashboard"""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_business_owner:
        messages.error(request, "Only business owners can access subscription dashboard.")
        return redirect('accounts:upgrade_to_business')
    
    # Get user's subscriptions
    subscriptions = UserSubscription.objects.filter(user=request.user).order_by('-start_date')
    
    # Get current active subscription
    active_subscription = subscriptions.filter(
        is_active=True, 
        expiry_date__gt=timezone.now()
    ).first()
    
    context = {
        'active_tab': 'subscription',
        'subscriptions': subscriptions,
        'active_subscription': active_subscription
    }
    
    return render(request, 'directory/dashboard/subscription.html', context)

@staff_member_required
def monitor_redis(request):
    """Monitor Redis connections"""
    try:
        # Connect to Redis
        r = redis.from_url(settings.REDIS_URL)
        
        # Get client list
        clients = r.client_list()
        
        return JsonResponse({
            'active_connections': len(clients),
            'clients': clients
        })
    except Exception as e:
        return JsonResponse({'error': str(e)})

# Add this helper function

def get_user_subscription(user):
    """Get active subscription details for a user"""
    return UserSubscription.objects.filter(
        user=user, 
        is_active=True, 
        expiry_date__gt=timezone.now()
    ).select_related('plan').first()

@login_required
def add_business_start(request):
    """Start the add business process by selecting a plan"""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_business_owner:
        messages.error(request, "You need to upgrade to a business owner account first.")
        return redirect('accounts:upgrade_to_business')
    
    # Redirect to subscription plans with a flag to indicate new business flow
    return redirect(f"{reverse('directory:subscription_plans')}?for_new_business=true")

def add_listings_info(request):
    """Add Listings information page"""
    return render(request, 'directory/add_listings_info.html')

def refer_earn(request):
    """Refer & Earn information page"""
    return render(request, 'directory/refer_earn.html')

def coming_soon(request):
    """Coming soon landing page"""
    return render(request, 'directory/coming_soon.html')

def about(request):
    """About us page"""
    return render(request, 'directory/about.html')

def terms(request):
    """Terms and Conditions page"""
    return render(request, 'directory/terms.html')

def privacy(request):
    """Privacy Policy page"""
    return render(request, 'directory/privacy.html')

def refund_policy(request):
    """Refund Policy page"""
    return render(request, 'directory/refund.html')

def contact(request):
    """Contact Us page"""
    return render(request, 'directory/contact.html')

# Add this new view for AJAX requests
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
from django.http import JsonResponse

@require_http_methods(["GET"])
def listings_ajax(request):
    """AJAX endpoint for infinite scroll"""
    page = request.GET.get('page', 1)
    
    # Same filtering logic as your main listings view
    businesses = Business.objects.filter(is_active=True).select_related('category', 'owner').prefetch_related('services', 'reviews')
    
    businesses = businesses.annotate(
        avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True)),
        approved_reviews_count=Count('reviews', filter=Q(reviews__is_approved=True))
    )
    
    # Apply same filters as main view
    category_id = request.GET.get('category')
    if category_id:
        businesses = businesses.filter(category_id=category_id)
    
    search_query = request.GET.get('query')
    if search_query:
        businesses = businesses.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query) |
            Q(services__name__icontains=search_query)
        ).distinct()
    
    rating = request.GET.get('rating')
    if rating:
        businesses = businesses.filter(reviews__rating__gte=int(rating)).distinct()
    
    pincode = request.GET.get('pincode')
    if pincode:
        businesses = businesses.filter(pincode__startswith=pincode)
    
    trust_filter = request.GET.get('trust')
    if trust_filter == 'gst':
        businesses = businesses.filter(gst_verified=True)
    elif trust_filter == 'kyc':
        businesses = businesses.filter(kyc_status='completed')
    elif trust_filter == 'both':
        businesses = businesses.filter(gst_verified=True, kyc_status='completed')
    
    # Pagination for AJAX
    paginator = Paginator(businesses, 10)  # 10 items per load
    page_obj = paginator.get_page(page)
    
    # Prepare business data
    business_data = []
    for business in page_obj.object_list:
        business_data.append({
            'id': business.id,
            'name': business.name,
            'description': business.description,
            'category': business.category.name,
            'city': business.city,
            'pincode': business.pincode,
            'image_url': business.get_primary_image_url(),
            'avg_rating': business.avg_rating or 0,
            'approved_reviews_count': business.approved_reviews_count,
            'gst_verified': business.gst_verified,
            'kyc_status': business.kyc_status,
            'owner_name': business.owner.get_full_name() or business.owner.username,
            'services': [service.name for service in business.services.all()[:5]],
            'services_count': business.services.count(),
        })
    
    return JsonResponse({
        'businesses': business_data,
        'has_next': page_obj.has_next(),
        'current_page': page_obj.number,
        'total_pages': paginator.num_pages,
        'total_count': paginator.count
    })

# In directory/views.py - Add this new view
@login_required
def dashboard_coupons(request):
    """Dashboard coupon requests view"""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_business_owner:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('directory:home')
    
    # Get user's businesses (only premium ones for coupon settings)
    user_businesses = Business.objects.filter(owner=request.user)
    premium_businesses = [b for b in user_businesses if b.has_premium_features]
    
    coupon_requests = CouponRequest.objects.filter(business__owner=request.user).order_by('-created_at')
    
    # Statistics
    total_coupons = coupon_requests.count()
    pending_coupons = coupon_requests.filter(is_fulfilled=False).count()
    fulfilled_coupons = coupon_requests.filter(is_fulfilled=True).count()
    
    context = {
        'active_tab': 'coupons',
        'user_businesses': premium_businesses,  # Add this
        'coupon_requests': coupon_requests,
        'total_coupons': total_coupons,
        'pending_coupons': pending_coupons,
        'fulfilled_coupons': fulfilled_coupons,
    }
    
    return render(request, 'directory/dashboard/coupons.html', context)

@login_required
def mark_coupon_fulfilled(request):
    """Mark a coupon as fulfilled/used"""
    if request.method == 'POST':
        coupon_id = request.POST.get('coupon_id')
        coupon = get_object_or_404(CouponRequest, id=coupon_id, business__owner=request.user)
        
        coupon.is_fulfilled = True
        coupon.fulfilled_at = timezone.now()
        coupon.save()
        
        messages.success(request, f"Coupon {coupon.coupon_code} marked as fulfilled.")
    
    return redirect('directory:dashboard_coupons')

@login_required
def update_coupon_discount(request):
    """Update coupon discount percentage"""
    if request.method == 'POST':
        coupon_id = request.POST.get('coupon_id')
        discount = request.POST.get('discount_percentage', 20)
        
        try:
            discount = int(discount)
            if discount < 1 or discount > 90:
                messages.error(request, "Discount percentage must be between 1-90%")
                return redirect('directory:dashboard_coupons')
        except ValueError:
            messages.error(request, "Invalid discount percentage")
            return redirect('directory:dashboard_coupons')
        
        coupon = get_object_or_404(CouponRequest, id=coupon_id, business__owner=request.user)
        coupon.discount_percentage = discount
        coupon.save()
        
        messages.success(request, f"Discount updated to {discount}% for coupon {coupon.coupon_code}")
    
    return redirect('directory:dashboard_coupons')

# In directory/views.py
@login_required
def update_business_coupon_settings(request):
    """Update coupon settings for a specific business"""
    if request.method == 'POST':
        business_id = request.POST.get('business_id')
        discount = request.POST.get('discount_percentage', 20)
        enabled = request.POST.get('coupon_enabled') == 'on'
        
        try:
            business = get_object_or_404(Business, id=business_id, owner=request.user)
            business.coupon_discount = int(discount)
            business.coupon_enabled = enabled
            business.save()
            
            messages.success(request, f"Coupon settings updated for {business.name}")
        except Exception as e:
            messages.error(request, "Error updating coupon settings")
    
    return redirect('directory:dashboard_coupons')