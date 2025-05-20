from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from .forms import UserRegisterForm
from directory.models import Business
from django.contrib.auth.models import User

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        print(f"Form valid: {form.is_valid()}")
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Welcome to BizDirectory, {username}! Your account has been created.')
            
            # Automatically log in the user
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            
            # Redirect based on user type
            if user.profile.is_business_owner:
                return redirect('directory:dashboard_home')
            else:
                return redirect('directory:home')
        else:
            print(f"Form errors: {form.errors}")
    else:
        form = UserRegisterForm()
    
    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Try to authenticate with username
        user = authenticate(request, username=username, password=password)
        
        # If authentication fails, try with email
        if user is None:
            try:
                user_obj = User.objects.get(email=username)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass
                
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            
            # Get the next parameter or redirect based on user type
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            elif hasattr(user, 'profile') and user.profile.is_business_owner:
                return redirect('directory:dashboard_home')
            else:
                return redirect('directory:home')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'accounts/login.html')

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('directory:home')

@login_required
def profile(request):
    if hasattr(request.user, 'profile') and request.user.profile.is_business_owner:
        # For business owners, redirect to dashboard
        return redirect('directory:dashboard_home')
    # For regular users, show profile page
    return render(request, 'accounts/profile.html')
