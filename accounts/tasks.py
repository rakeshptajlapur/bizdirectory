# Ensure Celery auto-discovers the tasks
from .signals import send_welcome_email
from .signals import send_password_changed_email
from .signals import send_password_reset_email
from .signals import send_profile_updated_email
