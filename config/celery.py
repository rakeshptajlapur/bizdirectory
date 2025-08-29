import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in installed apps
app.autodiscover_tasks()

# FIX: Update timeout settings for email tasks
app.conf.update(
    task_soft_time_limit=60,      # Increased from 30
    task_time_limit=120,          # Increased from 60
    task_reject_on_worker_lost=True,
    worker_hijack_root_logger=False,
)

# FIX: Optimize connection settings
app.conf.update(
    worker_prefetch_multiplier=1,
    broker_pool_limit=None,       # Remove connection limit
    task_acks_late=True,
    broker_connection_timeout=30,  # Increased timeout
    broker_connection_max_retries=3,
    broker_connection_retry=True,
    result_expires=3600,  # Keep results for 1 hour
)
