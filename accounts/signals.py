from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile
from celery import shared_task
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.core.mail import send_mail

@shared_task
def send_welcome_email(user_id):
    user = User.objects.get(id=user_id)
    context = {'user': user}
    subject = "Welcome to FindNearBiz!"
    html_message = render_to_string('emails/welcome.html', context)
    text_message = strip_tags(html_message)
    send_mail(subject, text_message, settings.DEFAULT_FROM_EMAIL, [user.email], html_message=html_message)

@shared_task
def send_password_changed_email(user_id):
    user = User.objects.get(id=user_id)
    context = {'user': user}
    subject = "Your password has been changed"
    html_message = render_to_string('emails/password_changed.html', context)
    text_message = strip_tags(html_message)
    send_mail(subject, text_message, settings.DEFAULT_FROM_EMAIL, [user.email], html_message=html_message)

@shared_task
def send_password_reset_email(user_id, reset_url):
    """Send a password reset email via Celery"""
    print(f"DEBUG: Celery task send_password_reset_email called with user_id={user_id}, reset_url={reset_url}")
    try:
        user = User.objects.get(id=user_id)
        context = {
            'user': user,
            'reset_url': reset_url,
            'site_name': 'BizDirectory'
        }
        subject = "Reset your BizDirectory password"
        html_message = render_to_string('accounts/password_reset_email.html', context)
        text_message = strip_tags(html_message)
        print(f"DEBUG: Attempting to send password reset email to {user.email}")
        send_mail(subject, text_message, settings.DEFAULT_FROM_EMAIL, [user.email], html_message=html_message)
        print(f"DEBUG: Password reset email sent successfully to {user.email}")
    except Exception as e:
        print(f"ERROR: Failed to send password reset email: {str(e)}")
        # Re-raise the exception to ensure it's logged properly by Celery
        raise

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