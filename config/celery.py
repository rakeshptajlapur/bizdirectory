import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in installed apps
app.autodiscover_tasks()

# Add these timeout settings
app.conf.update(
    task_soft_time_limit=30,
    task_time_limit=60,
)

# Reduce connection usage
app.conf.update(
    worker_prefetch_multiplier=1,  # Fetch one task at a time
    broker_pool_limit=10,  # Limit broker connections per worker
    task_acks_late=True,    # Acknowledge after task completes
    broker_connection_timeout=5,  # Timeout for broker connection
    broker_connection_max_retries=0,  # Don't retry connections endlessly
    broker_connection_retry=False,  # Don't retry connections automatically
)
