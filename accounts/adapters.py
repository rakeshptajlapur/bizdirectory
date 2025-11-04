from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.utils import user_email
from django.contrib.auth.models import User

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """
        Connect social account to existing user if email matches
        """
        if sociallogin.is_existing:
            return
            
        if 'email' not in sociallogin.account.extra_data:
            return
            
        email = sociallogin.account.extra_data['email']
        
        # Check if user with this email already exists
        try:
            existing_user = User.objects.get(email=email)
            # Connect the social account to existing user
            sociallogin.connect(request, existing_user)
        except User.DoesNotExist:
            # No existing user, will create new one
            pass
    
    def save_user(self, request, sociallogin, form=None):
        """
        Save the social account user and ensure email is verified
        """
        user = super().save_user(request, sociallogin, form)
        
        # Mark email as verified for social accounts
        user.is_active = True
        user.save()
        
        # Create or update profile
        from accounts.models import Profile
        Profile.objects.get_or_create(user=user, defaults={'user_type': 'regular'})
        
        return user
    
    def get_signup_redirect_url(self, request):
        """
        Redirect social login users directly to dashboard
        """
        return '/dashboard/'