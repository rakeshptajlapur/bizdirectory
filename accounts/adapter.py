from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.contrib.auth.models import User

class CustomAccountAdapter(DefaultAccountAdapter):
    """Custom allauth adapter that uses Celery for emails"""
    
    def send_mail(self, template_prefix, email, context):
        """Override email sending to use Celery tasks"""
        # Get the user
        user = context.get('user')
        if not user:
            # Try to find the user by email
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                # Fall back to default behavior if user not found
                return super().send_mail(template_prefix, email, context)
        
        # Route different email types to different Celery tasks
        if template_prefix == 'account/email/email_confirmation':
            # Email verification
            activation_url = context.get('activate_url')
            # For OTP-based verification, extract the code
            activation_key = context.get('key')
            if activation_key:
                from .signals import send_verification_email
                send_verification_email.delay(user.id, activation_key)
                return
                
        elif template_prefix == 'account/email/password_reset_key':
            # Password reset
            reset_url = context.get('password_reset_url')
            if reset_url:
                from .signals import send_password_reset_email
                send_password_reset_email.delay(user.id, reset_url)
                return
                
        elif template_prefix == 'account/email/email_confirmation_signup':
            # Welcome email after signup verification
            from .signals import send_welcome_email
            send_welcome_email.delay(user.id)
            return
            
        # Fall back to default behavior for any other emails
        return super().send_mail(template_prefix, email, context)