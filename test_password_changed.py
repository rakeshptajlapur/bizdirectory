"""
Test script for the password changed email notification
"""
import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Django imports
from django.contrib.auth.models import User
from accounts.signals import send_password_changed_email

# Use the first user's email from the database
TEST_EMAIL = User.objects.first().email if User.objects.exists() else "test@example.com"

def test_password_changed_email():
    """Test the password changed email notification"""
    print("Testing password changed email notification")
    try:
        # Get user
        user = User.objects.get(email=TEST_EMAIL)
        print(f"Found user: {user.username}, ID: {user.id}")
        
        # Call the task directly (not via Celery)
        print("Calling send_password_changed_email function directly...")
        send_password_changed_email(user.id)
        print("Direct call completed")
        
        # Call via Celery
        print("Calling send_password_changed_email via Celery...")
        task = send_password_changed_email.delay(user.id)
        print(f"Celery task ID: {task.id}")
        print("Remember to check the Celery worker logs for more information")
    
    except User.DoesNotExist:
        print(f"No user found with email: {TEST_EMAIL}")
        print("Please edit this script to use a valid email address")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_password_changed_email()
