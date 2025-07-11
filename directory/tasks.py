# This tasks module ensures Celery discovers shared tasks defined in signals.py
from .signals import (
    send_notification_email,
    send_enquiry_ack_email,
    send_enquiry_owner_email,
    send_coupon_user_ack_email,
    send_coupon_owner_notification_email,
)
