from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile
from celery import shared_task
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.core.mail import send_mail

@shared_task(bind=True, priority=5)  # Medium priority for welcome emails
def send_welcome_email(self, user_id):
    try:
        user = User.objects.get(id=user_id)
        
        # Simple welcome email without template rendering
        subject = "Welcome to FindNearBiz!"
        message = f"""
Hi {user.first_name or user.username},

Welcome to FindNearBiz! Your account has been successfully created.

You can now start exploring local businesses and services in your area.

Best regards,
FindNearBiz Team
        """
        
        send_mail(
            subject, 
            message.strip(), 
            settings.DEFAULT_FROM_EMAIL, 
            [user.email],
            fail_silently=False
        )
        
    except Exception as e:
        print(f"ERROR: Failed to send welcome email: {str(e)}")
        raise self.retry(countdown=60 * (2 ** self.request.retries), max_retries=3)
    finally:
        from django.db import connection
        connection.close()

@shared_task(bind=True, priority=7)  # High priority for security notifications
def send_password_changed_email(self, user_id):
    try:
        user = User.objects.get(id=user_id)
        
        # Simple security notification without template rendering
        subject = "Your password has been changed - FindNearBiz"
        message = f"""
Hi {user.first_name or user.username},

Your password has been successfully changed.

If you did not make this change, please contact us immediately.

Best regards,
FindNearBiz Team
        """
        
        send_mail(
            subject, 
            message.strip(), 
            settings.DEFAULT_FROM_EMAIL, 
            [user.email],
            fail_silently=False
        )
        
    except Exception as e:
        print(f"ERROR: Failed to send password changed email: {str(e)}")
        raise self.retry(countdown=60 * (2 ** self.request.retries), max_retries=3)
    finally:
        from django.db import connection
        connection.close()

@shared_task(bind=True, priority=8)  # High priority for password resets
def send_password_reset_email(self, user_id, reset_url):
    """Send a password reset email via Celery"""
    try:
        user = User.objects.get(id=user_id)
        
        # Simple password reset email without template rendering
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
        
        send_mail(
            subject, 
            message.strip(), 
            settings.DEFAULT_FROM_EMAIL, 
            [user.email],
            fail_silently=False
        )
        
    except Exception as e:
        print(f"ERROR: Failed to send password reset email: {str(e)}")
        raise self.retry(countdown=60 * (2 ** self.request.retries), max_retries=3)
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

@shared_task(bind=True, priority=9)  # High priority for verification emails
def send_verification_email(self, user_id, otp_code):
    try:
        user = User.objects.get(id=user_id)
        
        # Simple, fast email without heavy templates
        subject = "Verify your email address - FindNearBiz"
        message = f"""
Hi {user.first_name or user.username},

Your verification code is: {otp_code}

This code will expire in 10 minutes.

Best regards,
FindNearBiz Team
        """
        
        # Send plain text email for speed (no HTML rendering)
        send_mail(
            subject, 
            message.strip(), 
            settings.DEFAULT_FROM_EMAIL, 
            [user.email],
            fail_silently=False
        )
        
    except Exception as e:
        print(f"ERROR: Failed to send verification email: {str(e)}")
        # Retry with exponential backoff
        raise self.retry(countdown=60 * (2 ** self.request.retries), max_retries=3)
    finally:
        # Close connections to prevent leaks
        from django.db import connection
        connection.close()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        # Send welcome email
        send_welcome_email.delay(instance.id)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()