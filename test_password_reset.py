"""
Test script for the password reset email feature
"""
import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Django imports
from django.contrib.auth.models import User
from accounts.signals import send_password_reset_email

# Use the first user's email from the database
from django.contrib.auth.models import User
TEST_EMAIL = User.objects.first().email if User.objects.exists() else "test@example.com"

def test_password_reset():
    """Test the password reset functionality"""
    print("Testing password reset email")
    try:
        # Get user
        user = User.objects.get(email=TEST_EMAIL)
        print(f"Found user: {user.username}, ID: {user.id}")
        
        # Test reset URL
        reset_url = "http://example.com/reset/test-uid/test-token/"
        print(f"Using test reset URL: {reset_url}")
        
        # Call the task directly (not via Celery)
        print("Calling send_password_reset_email function directly...")
        send_password_reset_email(user.id, reset_url)
        print("Direct call completed")
        
        # Call via Celery
        print("Calling send_password_reset_email via Celery...")
        task = send_password_reset_email.delay(user.id, reset_url)
        print(f"Celery task ID: {task.id}")
        print("Remember to check the Celery worker logs for more information")
    
    except User.DoesNotExist:
        print(f"No user found with email: {TEST_EMAIL}")
        print("Please edit this script to use a valid email address")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_password_reset()
