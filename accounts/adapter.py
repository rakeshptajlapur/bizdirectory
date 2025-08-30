from allauth.account.adapter import DefaultAccountAdapter
from django.contrib.auth.models import User
from django.conf import settings
import os

class CustomAccountAdapter(DefaultAccountAdapter):
    """Custom adapter for allauth that uses Celery tasks for all emails"""
    
    def send_mail(self, template_prefix, email, context):
        """Override email sending to use Celery tasks"""
        print(f"DEBUG: Custom adapter sending email with template_prefix: {template_prefix}")
        
        # Get the user object
        user = None
        if 'user' in context:
            user = context['user']
        if not user and email:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                # Fall back to default behavior if user not found
                return super().send_mail(template_prefix, email, context)
        
        # Route different email types to different Celery tasks
        if not user:
            print("WARNING: No user found for email task, falling back to default")
            return super().send_mail(template_prefix, email, context)
            
        if template_prefix == 'account/email/email_confirmation':
            # Email verification
            from .signals import send_verification_email
            
            # Get the key or URL from context
            key = None
            if 'key' in context:
                key = context['key']
                # Get the full activation URL
                activate_url = context.get('activate_url', '')
                print(f"DEBUG: Activation URL: {activate_url}")
                if not activate_url:
                    # Build the activation URL
                    site = context.get('current_site')
                    activate_url = f"http://{site.domain}/accounts/confirm-email/{key}/"
                
                # Send verification email with the URL
                print(f"DEBUG: Sending verification email to user {user.id} with key {key}")
                send_verification_email.delay(user.id, activate_url)
                return
                
        elif template_prefix == 'account/email/password_reset_key':
            # Password reset
            from .signals import send_password_reset_email
            
            # Get the URL from context
            password_reset_url = context.get('password_reset_url', '')
            if not password_reset_url:
                # Build the reset URL
                site = context.get('current_site')
                uid = context.get('uid')
                token = context.get('token')
                password_reset_url = f"http://{site.domain}/accounts/password/reset/key/{uid}-{token}/"
                
            print(f"DEBUG: Sending password reset email to user {user.id} with URL {password_reset_url}")
            send_password_reset_email.delay(user.id, password_reset_url)
            return
                
        elif template_prefix == 'account/email/email_confirmation_signup':
            # Welcome email after signup verification
            from .signals import send_welcome_email
            print(f"DEBUG: Sending welcome email to user {user.id}")
            send_welcome_email.delay(user.id)
            return
            
        # Fall back to default behavior for any other emails
        print(f"DEBUG: Using default email sending for template_prefix {template_prefix}")
        return super().send_mail(template_prefix, email, context)