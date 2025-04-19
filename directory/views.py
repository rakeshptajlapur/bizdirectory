from django.shortcuts import render, get_object_or_404
from django.db.models import Q, Avg, Count
from django.http import JsonResponse
from .models import Business, Category, Service  # Make sure to import Service

def home(request):
    search_query = request.GET.get('query', '')
    selected_category = request.GET.get('category', '')
    selected_pincode = request.GET.get('pincode', '')
    
    businesses = Business.objects.filter(is_active=True)
    
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
    business = get_object_or_404(Business, pk=pk)
    context = {
        'business': business
    }
    return render(request, 'directory/business_detail.html', context)

def search_suggestions(request):
    query = request.GET.get('term', '')
    if len(query) < 2:
        return JsonResponse([], safe=False)
    
    # Get businesses that match the query
    businesses = Business.objects.filter(
        Q(name__icontains=query) | 
        Q(description__icontains=query)
    ).values_list('name', flat=True).distinct()[:10]
    
    # Also get matching services
    services = Service.objects.filter(
        name__icontains=query
    ).values_list('name', flat=True).distinct()[:5]
    
    # Combine and deduplicate results
    suggestions = list(businesses) + list(services)
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
