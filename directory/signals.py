from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.core.mail import send_mail
from celery import shared_task
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import Business, Enquiry, CouponRequest
import logging
import uuid

logger = logging.getLogger(__name__)

@shared_task
def send_notification_email(subject, message, recipient_list):
    sent_count = send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list, fail_silently=False)
    logger.info(f"send_mail returned: {sent_count}")
    return sent_count

# Example: Send notification when a new business is created (pending approval)
@receiver(post_save, sender=Business)
def business_created_notification(sender, instance, created, **kwargs):
    if created and not instance.is_approved:
        subject = f"New Business Listing Pending Approval: {instance.name}"
        message = f"A new business listing '{instance.name}' has been submitted and is pending approval."
        # Send to admin (replace with your admin email)
        send_notification_email.delay(subject, message, [settings.DEFAULT_FROM_EMAIL])

# Add tasks and receivers for Enquiry notifications
@shared_task
def send_enquiry_ack_email(enquiry_id):
    enquiry = Enquiry.objects.get(id=enquiry_id)
    context = {'enquiry': enquiry}
    subject = f"Thank you for your enquiry about {enquiry.business.name}"
    html_message = render_to_string('emails/enquiry_ack.html', context)
    text_message = strip_tags(html_message)
    send_mail(subject, text_message, settings.DEFAULT_FROM_EMAIL, [enquiry.email], html_message=html_message)

@shared_task
def send_enquiry_owner_email(enquiry_id):
    enquiry = Enquiry.objects.get(id=enquiry_id)
    context = {'enquiry': enquiry}
    subject = f"New enquiry for {enquiry.business.name}"
    html_message = render_to_string('emails/enquiry_notify_owner.html', context)
    text_message = strip_tags(html_message)
    # Send notifications to the business owner’s account email and admin
    recipients = [enquiry.business.owner.email, settings.DEFAULT_FROM_EMAIL]
    send_mail(subject, text_message, settings.DEFAULT_FROM_EMAIL, recipients, html_message=html_message)

@receiver(post_save, sender=Enquiry)
def enquiry_notifications(sender, instance, created, **kwargs):
    if created:
        send_enquiry_ack_email.delay(instance.id)
        send_enquiry_owner_email.delay(instance.id)

# Add tasks and receivers for CouponRequest notifications
@shared_task
def send_coupon_user_ack_email(coupon_id):
    coupon = CouponRequest.objects.get(id=coupon_id)
    # Generate code if not present
    if not coupon.coupon_code:
        coupon.coupon_code = uuid.uuid4().hex[:8].upper()
        coupon.save(update_fields=['coupon_code'])
    context = {'coupon': coupon}
    subject = f"Your coupon code for {coupon.business.name}"
    html_message = render_to_string('emails/coupon_ack.html', context)
    text_message = strip_tags(html_message)
    send_mail(subject, text_message, settings.DEFAULT_FROM_EMAIL, [coupon.email], html_message=html_message)
    coupon.is_sent = True
    coupon.save(update_fields=['is_sent'])

@shared_task
def send_coupon_owner_notification_email(coupon_id):
    coupon = CouponRequest.objects.get(id=coupon_id)
    context = {'coupon': coupon}
    subject = f"New coupon request by {coupon.email}"
    html_message = render_to_string('emails/coupon_notify_owner.html', context)
    text_message = strip_tags(html_message)
    # Notify the business owner’s account email and admin
    recipients = [coupon.business.owner.email, settings.DEFAULT_FROM_EMAIL]
    send_mail(subject, text_message, settings.DEFAULT_FROM_EMAIL, recipients, html_message=html_message)

@receiver(post_save, sender=CouponRequest)
def coupon_request_notifications(sender, instance, created, **kwargs):
    if created:
        send_coupon_user_ack_email.delay(instance.id)
        send_coupon_owner_notification_email.delay(instance.id)
