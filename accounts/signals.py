from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile
from celery import shared_task
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.core.mail import send_mail

@shared_task(priority=9)
def send_verification_email(user_id, verification_code_or_url):
    try:
        user = User.objects.get(id=user_id)
        
        # Determine if we're sending an OTP or a verification URL
        is_otp = len(verification_code_or_url) <= 10  # OTPs are usually 6 digits
        
        print(f"DEBUG: Sending verification email to {user.email}")
        
        subject = "Verify your email address - FindNearBiz"
        
        if is_otp:
            # OTP-style verification
            otp_code = verification_code_or_url
            message = f"""
Hi {user.first_name or user.username},

Your verification code is: {otp_code}

This code will expire in 30 minutes.

Best regards,
FindNearBiz Team
            """
        else:
            # URL-style verification
            verify_url = verification_code_or_url
            message = f"""
Hi {user.first_name or user.username},

Please verify your email address by clicking the link below:

{verify_url}

This link will expire in 30 minutes.

Best regards,
FindNearBiz Team
            """
        
        result = send_mail(
            subject, 
            message.strip(), 
            settings.DEFAULT_FROM_EMAIL, 
            [user.email],
            fail_silently=False
        )
        
        print(f"DEBUG: Email sent successfully. Result: {result}")
        return result
        
    except Exception as e:
        print(f"ERROR: Failed to send verification email: {str(e)}")
        raise
    finally:
        from django.db import connection
        connection.close()

@shared_task(priority=5)  # Removed bind=True
def send_welcome_email(user_id):
    try:
        user = User.objects.get(id=user_id)
        
        print(f"DEBUG: Sending welcome email to {user.email}")
        
        subject = "Welcome to FindNearBiz!"
        message = f"""
Hi {user.first_name or user.username},

Welcome to FindNearBiz! Your account has been successfully created.

You can now:
- Search for local businesses
- Write reviews
- Contact businesses directly

Thank you for joining us!

Best regards,
FindNearBiz Team
        """
        
        result = send_mail(
            subject,
            message.strip(),
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False
        )
        
        print(f"DEBUG: Welcome email sent successfully. Result: {result}")
        return result
        
    except Exception as e:
        print(f"ERROR: Failed to send welcome email: {str(e)}")
        raise
    finally:
        from django.db import connection
        connection.close()

@shared_task(priority=7)  # Removed bind=True
def send_password_changed_email(user_id):
    try:
        user = User.objects.get(id=user_id)
        
        subject = "Your password has been changed - FindNearBiz"
        message = f"""
Hi {user.first_name or user.username},

Your password has been successfully changed.

If you did not make this change, please contact us immediately.

Best regards,
FindNearBiz Team
        """
        
        result = send_mail(
            subject, 
            message.strip(), 
            settings.DEFAULT_FROM_EMAIL, 
            [user.email],
            fail_silently=False
        )
        
        return result
        
    except Exception as e:
        print(f"ERROR: Failed to send password changed email: {str(e)}")
        raise
    finally:
        from django.db import connection
        connection.close()

@shared_task(priority=8)  # Removed bind=True  
def send_password_reset_email(user_id, reset_url):
    """Send a password reset email via Celery"""
    try:
        user = User.objects.get(id=user_id)
        
        subject = "Reset your FindNearBiz password"
        message = f"""
Hi {user.first_name or user.username},

You requested to reset your password for FindNearBiz.

Click the link below to reset your password:
{reset_url}

If you didn't request this, please ignore this email.

Best regards,
FindNearBiz Team
        """
        
        result = send_mail(
            subject, 
            message.strip(), 
            settings.DEFAULT_FROM_EMAIL, 
            [user.email],
            fail_silently=False
        )
        
        return result
        
    except Exception as e:
        print(f"ERROR: Failed to send password reset email: {str(e)}")
        raise
    finally:
        from django.db import connection
        connection.close()

@shared_task
def send_profile_updated_email(user_id):
    """Send a profile update confirmation email via Celery"""
    try:
        user = User.objects.get(id=user_id)
        context = {
            'user': user,
            'site_name': 'BizDirectory'
        }
        subject = "Your profile has been updated"
        html_message = render_to_string('emails/profile_updated.html', context)
        text_message = strip_tags(html_message)
        send_mail(subject, text_message, settings.DEFAULT_FROM_EMAIL, [user.email], html_message=html_message)
    except Exception as e:
        print(f"ERROR: Failed to send profile update email: {str(e)}")
        # Re-raise the exception to ensure it's logged properly by Celery
        raise
    finally:
        # Close connections to prevent leaks
        from django.db import connection
        connection.close()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)
        # DON'T send welcome email here - only after email verification

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()