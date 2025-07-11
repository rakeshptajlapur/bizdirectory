"""
Test script for all account lifecycle email notifications
"""
import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Django imports
from django.contrib.auth.models import User
from accounts.signals import (
    send_welcome_email, 
    send_password_changed_email, 
    send_password_reset_email,
    send_profile_updated_email
)

# Use the first user's email from the database
TEST_EMAIL = User.objects.first().email if User.objects.exists() else "test@example.com"

def test_all_email_notifications():
    """Test all email notifications in the account lifecycle"""
    print("\n======== TESTING ALL EMAIL NOTIFICATIONS ========\n")
    
    try:
        # Get user
        user = User.objects.get(email=TEST_EMAIL)
        print(f"Using user: {user.username}, ID: {user.id}, Email: {user.email}\n")
        
        # 1. Test Welcome Email
        print("1. TESTING WELCOME EMAIL")
        print("------------------------")
        print("Calling send_welcome_email directly...")
        try:
            send_welcome_email(user.id)
            print("✓ Welcome email sent directly")
        except Exception as e:
            print(f"✗ Error sending welcome email: {str(e)}")
        print("")
        
        # 2. Test Password Changed Email
        print("2. TESTING PASSWORD CHANGED EMAIL")
        print("--------------------------------")
        print("Calling send_password_changed_email directly...")
        try:
            send_password_changed_email(user.id)
            print("✓ Password changed email sent directly")
        except Exception as e:
            print(f"✗ Error sending password changed email: {str(e)}")
        print("")
        
        # 3. Test Password Reset Email
        print("3. TESTING PASSWORD RESET EMAIL")
        print("------------------------------")
        print("Calling send_password_reset_email directly...")
        test_reset_url = "http://example.com/accounts/reset/test-uid/test-token/"
        try:
            send_password_reset_email(user.id, test_reset_url)
            print("✓ Password reset email sent directly")
        except Exception as e:
            print(f"✗ Error sending password reset email: {str(e)}")
        print("")
        
        # 4. Test Profile Updated Email
        print("4. TESTING PROFILE UPDATED EMAIL")
        print("-------------------------------")
        print("Calling send_profile_updated_email directly...")
        try:
            send_profile_updated_email(user.id)
            print("✓ Profile updated email sent directly")
        except Exception as e:
            print(f"✗ Error sending profile updated email: {str(e)}")
        print("")
        
        print("======== ALL TESTS COMPLETED ========")
    
    except User.DoesNotExist:
        print(f"No user found with email: {TEST_EMAIL}")
    except Exception as e:
        print(f"Error during testing: {str(e)}")

if __name__ == "__main__":
    test_all_email_notifications()
