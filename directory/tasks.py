# This tasks module ensures Celery discovers shared tasks defined in signals.py
from .signals import (
    send_notification_email,
    send_enquiry_ack_email,
    send_enquiry_owner_email,
    send_coupon_user_ack_email,
    send_coupon_owner_notification_email,
    send_review_ack_email,
    send_review_owner_pending_email,
    send_review_visible_email,
    send_business_live_email,
    send_business_deactivated_email,
)

# Import welcome email task from accounts to ensure Celery registers it
from accounts.signals import send_welcome_email
