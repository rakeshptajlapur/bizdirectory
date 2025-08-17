from django.shortcuts import render, get_object_or_404
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
import os
# Fix missing imports
from .models import Business, Category, Service, BusinessImage, BusinessHours, Review, Enquiry, CouponRequest


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
    """Auto-suggestions for search box"""
    term = request.GET.get('term', '')
    
    # Only include active businesses in suggestions
    suggestions = Business.objects.filter(
        Q(name__icontains=term) & 
        Q(is_active=True)
    ).values_list('name', flat=True)[:10]
    
    return JsonResponse(list(suggestions), safe=False)

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
    
    # Add this annotation to calculate approved reviews count
    businesses = businesses.annotate(
        avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True)),
        approved_reviews_count=Count('reviews', filter=Q(reviews__is_approved=True))
    )
    
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

def request_coupon(request, business_id):
    """Handle coupon form submissions"""
    business = get_object_or_404(Business, pk=business_id)
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        # Basic email validation
        if not email or '@' not in email or '.' not in email:
            messages.error(request, "Please provide a valid email address")
            return redirect('directory:business_detail', pk=business_id)
            
        try:
            # Generate a unique coupon code
            import random
            import string
            code_chars = string.ascii_uppercase + string.digits
            coupon_code = ''.join(random.choice(code_chars) for _ in range(8))
            
            # Check if this email already requested a coupon
            existing_coupon = CouponRequest.objects.filter(business=business, email=email).first()
            if existing_coupon:
                messages.info(request, f"You've already requested a coupon. Your code is: {existing_coupon.coupon_code}")
            else:
                # Create coupon request
                CouponRequest.objects.create(
                    business=business,
                    email=email,
                    coupon_code=coupon_code,
                    is_sent=True
                )
                messages.success(request, f"Success! Your discount code is: {coupon_code}")
                
        except Exception as e:
            messages.error(request, "Sorry, something went wrong. Please try again later.")
            print(f"Error processing coupon request: {str(e)}")
        
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
    
    # Get business for sidebar context
    business = None
    if hasattr(request.user, 'profile') and request.user.profile.is_business_owner:
        try:
            business = Business.objects.get(owner=request.user)
        except Business.DoesNotExist:
            pass
    
    context = {
        'active_tab': 'home',
        'business': business,  # Add this
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

@login_required
def dashboard_leads(request):
    """Dashboard leads view - combines enquiries, reviews and coupon requests"""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_business_owner:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('directory:home')
    
    # Get all businesses owned by the user
    businesses = Business.objects.filter(owner=request.user)
    
    # Get all enquiries and convert them to a common lead format
    enquiries = Enquiry.objects.filter(business__owner=request.user).select_related('business')
    enquiry_leads = []
    for enquiry in enquiries:
        enquiry_leads.append({
            'id': enquiry.id,
            'name': enquiry.name,
            'email': enquiry.email,
            'phone': enquiry.phone,
            'source': 'enquiry',
            'business': enquiry.business,
            'created_at': enquiry.created_at,
            'is_responded': enquiry.is_responded,
        })
    
    # Get all reviews and convert them to a common lead format
    reviews = Review.objects.filter(business__owner=request.user).select_related('business')
    review_leads = []
    for review in reviews:
        review_leads.append({
            'id': review.id,
            'name': review.name,
            'email': review.email,
            'phone': None,  # Reviews typically don't have phone numbers
            'source': 'review',
            'business': review.business,
            'created_at': review.created_at,
            'is_approved': review.is_approved,
        })
    
    # Add this new section for coupon requests
    coupons = CouponRequest.objects.filter(business__owner=request.user).select_related('business')
    coupon_leads = []
    for coupon in coupons:
        coupon_leads.append({
            'id': coupon.id,
            'name': '',  # No name available
            'email': coupon.email,
            'phone': None,
            'source': 'coupon',
            'business': coupon.business,
            'created_at': coupon.created_at,
            'coupon_code': coupon.coupon_code,
            'is_sent': coupon.is_sent,
        })
    
    # Combine and sort by date
    leads = sorted(enquiry_leads + review_leads + coupon_leads, 
                   key=lambda x: x['created_at'], reverse=True)
    
    context = {
        'active_tab': 'leads',
        'leads': leads,
        'businesses': businesses,
    }
    
    return render(request, 'directory/dashboard/leads.html', context)

@login_required
def kyc_gst_documents(request):
    """KYC & GST documents management view"""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_business_owner:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('directory:home')
    
    # Get user's business (assuming one business per user)
    try:
        business = Business.objects.get(owner=request.user)
    except Business.DoesNotExist:
        messages.error(request, "Please create a business listing first.")
        return redirect('directory:dashboard_home')
    
    if request.method == 'POST':
        # Handle form submission
        registration_number = request.POST.get('registration_number', '').strip()
        gst_number = request.POST.get('gst_number', '').strip()
        registration_document = request.FILES.get('registration_document')
        
        # Update business details
        if registration_number:
            business.registration_number = registration_number
        
        if gst_number:
            business.gst_number = gst_number
            # Reset GST verification when number changes
            if business.gst_number != gst_number:
                business.gst_verified = False
        
        if registration_document:
            business.registration_document = registration_document
            # Reset KYC status when new document is uploaded
            business.kyc_status = 'pending'
        
        business.save()
        
        messages.success(request, 'Documents updated successfully! Our team will review and verify them within 24-48 hours.')
        return redirect('directory:kyc_gst_documents')
    
    context = {
        'active_tab': 'kyc_gst',
        'business': business,
    }
    return render(request, 'directory/dashboard/kyc_gst.html', context)

@login_required
def business_form(request, business_id=None):
    """Add new business or edit existing business"""
    if not hasattr(request.user, 'profile') or not request.user.profile.is_business_owner:
        messages.error(request, "You need to upgrade to a business owner account first.")
        return redirect('accounts:upgrade_to_business')
    
    # Determine if editing or adding
    if business_id:
        business = get_object_or_404(Business, id=business_id, owner=request.user)
        is_edit = True
    else:
        business = None
        is_edit = False
    
    if request.method == 'POST':
        form = BusinessForm(request.POST, request.FILES, instance=business, user=request.user)
        
        if form.is_valid():
            business = form.save(commit=False)
            
            if not is_edit:
                business.owner = request.user
            
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
            
            business.save()
            
            # Handle primary image
            primary_image = request.FILES.get('primary_image')
            if primary_image:
                # Remove existing primary image
                BusinessImage.objects.filter(business=business, is_primary=True).delete()
                # Add new primary image
                BusinessImage.objects.create(
                    business=business,
                    image=primary_image,
                    is_primary=True,
                    caption=f"{business.name} - Main Image"
                )
            
            # Handle gallery images
            gallery_images = request.FILES.getlist('gallery_images')
            for img in gallery_images:
                BusinessImage.objects.create(
                    business=business,
                    image=img,
                    is_primary=False,
                    caption=f"{business.name} - Gallery Image"
                )
            
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
            
            messages.success(request, status_message)
            return redirect('directory:dashboard_listings')
        
        else:
            messages.error(request, 'Please correct the errors below.')
    
    else:
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