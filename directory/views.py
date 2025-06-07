from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Avg, Count
from django.http import JsonResponse
from django.core.paginator import Paginator
from datetime import datetime
from .models import Business, Category, Service
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from .models import Review, Enquiry

def home(request):
    search_query = request.GET.get('query', '')
    selected_category = request.GET.get('category', '')
    selected_pincode = request.GET.get('pincode', '')
    
    businesses = Business.objects.filter(is_active=True).prefetch_related('services')
    
    # Add this annotation for the average rating
    businesses = businesses.annotate(avg_rating=Avg('reviews__rating'))
    
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
    ).order_by('-business_count')[:10]  # Show top 10 categories
    
    context = {
        'businesses': businesses,
        'categories': categories,
        'search_query': search_query,
        'selected_category': selected_category,
        'selected_pincode': selected_pincode,
        'top_categories': top_categories
    }
    
    return render(request, 'directory/home.html', context)

def business_detail(request, pk):
    """View for displaying a single business listing"""
    business = get_object_or_404(Business, pk=pk)
    
    # Get today's weekday (0=Monday, 6=Sunday)
    today_weekday = datetime.now().weekday()
    
    # Calculate average rating from approved reviews
    business.avg_rating = business.reviews.filter(is_approved=True).aggregate(
        avg=Avg('rating')
    )['avg'] or 0
    
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
        'today_weekday': today_weekday,
        'related_businesses': related_businesses,
        'user_review': user_review,
        # Add any other context variables
    }
    
    return render(request, 'directory/business_detail.html', context)

def search_suggestions(request):
    term = request.GET.get('term', '')
    if len(term) < 2:
        return JsonResponse([], safe=False)
        
    # Search businesses
    businesses = Business.objects.filter(
        Q(name__icontains=term) | Q(description__icontains=term)
    ).values_list('name', flat=True).distinct()[:5]
    
    # Search services
    services = Service.objects.filter(
        name__icontains=term
    ).values_list('name', flat=True).distinct()[:5]
    
    # Combine and deduplicate results
    suggestions = list(businesses) + list(services)
    suggestions = list(dict.fromkeys(suggestions))[:8]  # Take up to 8 unique suggestions
    
    return JsonResponse(suggestions, safe=False)

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
    categories = Category.objects.all().order_by('name')
    
    # Create a dictionary organized by first letter
    categorized = {}
    for category in categories:
        first_letter = category.name[0].upper()
        if first_letter not in categorized:
            categorized[first_letter] = []
        categorized[first_letter].append(category)
    
    # Count businesses in each category
    for letter in categorized:
        for category in categorized[letter]:
            category.business_count = Business.objects.filter(category=category, is_active=True).count()
    
    return render(request, 'directory/categories.html', {'categorized': categorized})

def listings(request):
    """View for all business listings with filters"""
    
    # Base queryset with optimized queries
    businesses = Business.objects.filter(is_active=True).select_related('category', 'owner').prefetch_related('services', 'reviews')
    
    # Apply filters
    category_id = request.GET.get('category')
    if category_id:
        businesses = businesses.filter(category_id=category_id)
    
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
    
    search_query = request.GET.get('query')
    if search_query:
        businesses = businesses.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query) |
            Q(services__name__icontains=search_query)
        ).distinct()
    
    # Get all categories for the filter sidebar
    categories = Category.objects.all()
    
    # Pagination
    paginator = Paginator(businesses, 12)  # 12 businesses per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Prepare current filters for maintaining state
    current_filters = {}
    for param in ['category', 'rating', 'pincode', 'trust', 'query']:
        if request.GET.get(param):
            current_filters[param] = request.GET.get(param)
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'current_filters': current_filters,
    }
    
    return render(request, 'directory/listings.html', context)

# In your directory/views.py
def add_listing(request):
    """View for the add listing page"""
    return render(request, 'directory/add_listing.html')

def add_review(request, business_id):
    """Handle review submission without requiring authentication"""
    business = get_object_or_404(Business, pk=business_id)
    
    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name')
        email = request.POST.get('email')
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        # Validate input
        if not name or not email:
            messages.error(request, "Please provide your name and email")
            return redirect('directory:business_detail', pk=business_id)
            
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                messages.error(request, "Rating must be between 1 and 5")
                return redirect('directory:business_detail', pk=business_id)
        except (ValueError, TypeError):
            messages.error(request, "Invalid rating value")
            return redirect('directory:business_detail', pk=business_id)
            
        if not comment:
            messages.error(request, "Please provide a review comment")
            return redirect('directory:business_detail', pk=business_id)
        
        # Check if email has already reviewed this business
        existing_review = Review.objects.filter(business=business, email=email).first()
        if existing_review:
            # Update existing review
            existing_review.name = name
            existing_review.rating = rating
            existing_review.comment = comment
            existing_review.is_approved = False  # Reset approval on update
            existing_review.save()
            messages.success(request, "Your review has been updated and is pending approval.")
        else:
            # Create new review
            Review.objects.create(
                business=business,
                name=name,
                email=email,
                rating=rating,
                comment=comment,
                is_approved=False
            )
            messages.success(request, "Thank you! Your review has been submitted and is pending approval.")
        
        # Store email in session to identify returning reviewers
        request.session['reviewer_email'] = email
        
        return redirect('directory:business_detail', pk=business_id)
    
    # GET requests redirect back to business detail
    return redirect('directory:business_detail', pk=business_id)

def send_enquiry(request, business_id):
    """Handle enquiry form submissions"""
    business = get_object_or_404(Business, pk=business_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone', '')
        message = request.POST.get('message')
        
        # Validate input
        if not name or not email or not message:
            messages.error(request, "Please fill all required fields")
            return redirect('directory:business_detail', pk=business_id)
            
        # Create new enquiry
        Enquiry.objects.create(
            business=business,
            name=name,
            email=email,
            phone=phone,
            message=message
        )
        
        # Store email in session for future reference
        request.session['enquirer_email'] = email
        
        messages.success(request, "Thank you! Your enquiry has been sent to the business owner.")
        return redirect('directory:business_detail', pk=business_id)
    
    # GET requests redirect back to business detail
    return redirect('directory:business_detail', pk=business_id)

@login_required
def dashboard_home(request):
    """Dashboard home view"""
    # Make sure user is a business owner
    if not hasattr(request.user, 'profile') or not request.user.profile.is_business_owner:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('directory:home')
    
    # Get businesses owned by the current user
    businesses = Business.objects.filter(owner=request.user)
    
    # Get stats for all user's businesses
    enquiries_count = Enquiry.objects.filter(business__owner=request.user).count()
    reviews_count = Review.objects.filter(business__owner=request.user).count()
    
    # Calculate average rating across all businesses
    avg_rating = Review.objects.filter(
        business__owner=request.user
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
        'enquiries_count': enquiries_count,
        'reviews_count': reviews_count,
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