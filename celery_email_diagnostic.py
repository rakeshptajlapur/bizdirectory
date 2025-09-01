# enhanced_email_diagnostic.py

import os
import django
import time
from datetime import datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.mail import send_mail, get_connection
from django.conf import settings
from django.contrib.auth.models import User
from django.db import connections
from celery import shared_task
import logging
from directory.models import Enquiry, Business

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_direct_smtp():
    """Test direct SMTP connection without Celery"""
    print("\n==== TESTING DIRECT SMTP ====")
    try:
        # Force SMTP backend
        connection = get_connection(
            backend='django.core.mail.backends.smtp.EmailBackend',
            host=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            username=settings.EMAIL_HOST_USER,
            password=settings.EMAIL_HOST_PASSWORD,
            use_tls=settings.EMAIL_USE_TLS,
            fail_silently=False
        )
        
        timestamp = int(time.time())
        subject = f"Direct SMTP Test [{timestamp}]"
        message = f"This is a direct SMTP test at {datetime.now()}"
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient = "rakeshptajlapur@gmail.com"
        
        result = send_mail(
            subject,
            message,
            from_email,
            [recipient],
            connection=connection
        )
        
        print(f"✅ Direct email sent successfully! Result: {result}")
        return True
    except Exception as e:
        print(f"❌ Direct email failed: {str(e)}")
        return False

def test_database_connection():
    """Test database connection"""
    print("\n==== TESTING DATABASE CONNECTION ====")
    try:
        # Force close and reopen connections
        connections.close_all()
        
        # Try to access user table
        user_count = User.objects.count()
        print(f"✅ Found {user_count} users in database")
        
        # Try to get first business
        business = Business.objects.first()
        if business:
            print(f"✅ Found business: {business.name} (ID: {business.id})")
            print(f"   Owned by: {business.owner.username} (ID: {business.owner.id})")
            return business
        else:
            print("❌ No businesses found in database")
            return None
    except Exception as e:
        print(f"❌ Database connection error: {str(e)}")
        return None

@shared_task(name="diagnostic.enquiry_email_test")
def test_send_enquiry_email(enquiry_id):
    """Test task that mimics send_enquiry_ack_email from directory/signals.py"""
    print(f"Starting test_send_enquiry_email task for enquiry ID: {enquiry_id}")
    try:
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags
        
        # Force close and reopen connections
        connections.close_all()
        
        # Get enquiry from database
        enquiry = Enquiry.objects.get(id=enquiry_id)
        print(f"✅ Found enquiry in database: {enquiry.name} to {enquiry.business.name}")
        
        context = {'enquiry': enquiry}
        subject = f"TEST - Thank you for your enquiry about {enquiry.business.name}"
        html_message = render_to_string('emails/enquiry_ack.html', context)
        text_message = strip_tags(html_message)
        
        # Force SMTP backend
        connection = get_connection(
            backend='django.core.mail.backends.smtp.EmailBackend',
            host=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            username=settings.EMAIL_HOST_USER,
            password=settings.EMAIL_HOST_PASSWORD,
            use_tls=settings.EMAIL_USE_TLS,
            fail_silently=False
        )
        
        result = send_mail(
            subject, 
            text_message, 
            settings.DEFAULT_FROM_EMAIL, 
            ["rakeshptajlapur@gmail.com"],  # Force send to test address
            html_message=html_message,
            connection=connection
        )
        
        print(f"✅ Enquiry email sent successfully. Result: {result}")
        return f"Email sent: {result}"
    except Exception as e:
        print(f"❌ Task failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}"
    finally:
        # Always close connections
        connections.close_all()

if __name__ == "__main__":
    print("\n===== COMPREHENSIVE CELERY EMAIL DIAGNOSTIC =====")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Using EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"Using EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"Using BROKER_URL: {settings.CELERY_BROKER_URL}")
    
    # Phase 1: Test direct SMTP
    smtp_ok = test_direct_smtp()
    
    # Phase 2: Test database connection
    business = test_database_connection()
    
    if smtp_ok and business:
        print("\n==== TESTING CELERY TASK EXECUTION ====")
        
        # Phase 3: Try to create a test enquiry
        try:
            # Create or get a test enquiry
            test_enquiry = Enquiry.objects.filter(business=business).first()
            if not test_enquiry:
                test_enquiry = Enquiry.objects.create(
                    business=business,
                    name="Diagnostic Test",
                    email="rakeshptajlapur@gmail.com",
                    phone="1234567890",
                    message="This is an automated test enquiry from diagnostic tool"
                )
                print(f"✅ Created test enquiry ID: {test_enquiry.id}")
            else:
                print(f"✅ Using existing enquiry ID: {test_enquiry.id}")
            
            # Phase 4: Queue test task
            print("\n==== QUEUING CELERY TASK ====")
            task_result = test_send_enquiry_email.delay(test_enquiry.id)
            print(f"✅ Task queued with ID: {task_result.id}")
            
            print("\n==== CHECK CELERY WORKER LOGS ====")
            print("1. Look for database connection errors")
            print("2. Check if the task is actually executed")
            print("3. Verify if SMTP email sending works from within the task")
            
            print("\n==== FINAL CHECKS ====")
            from config.celery import app
            i = app.control.inspect()
            
            # Check worker status
            active_queues = i.active_queues()
            if active_queues:
                print(f"Active queues: {list(active_queues.keys())}")
                for worker, queues in active_queues.items():
                    print(f"Worker {worker} is consuming from queues: {[q['name'] for q in queues]}")
            else:
                print("❌ No active Celery workers found!")
            
            # Check active tasks
            active_tasks = i.active()
            if active_tasks:
                print(f"Active tasks: {active_tasks}")
            else:
                print("No active tasks currently running")
                
            # Check reserved tasks
            reserved = i.reserved()
            if reserved:
                print(f"Reserved tasks: {reserved}")
        except Exception as e:
            print(f"❌ Test failed: {str(e)}")
    else:
        print("\n==== SKIPPING CELERY TESTS ====")
        print("Fix direct SMTP and database connection issues first.")
        
    print("\n===== DIAGNOSTIC COMPLETE =====")