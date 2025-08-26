# directory/management/commands/test_production_system.py
"""
Django management command to test the complete system in production
Usage: python manage.py test_production_system
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from datetime import datetime
import time

from accounts.models import EmailVerification
from accounts.signals import send_verification_email, send_welcome_email

class Command(BaseCommand):
    help = 'Test the complete registration and email system in production'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Test email address to use (default: auto-generate)',
            default=None
        )
        parser.add_argument(
            '--skip-registration',
            action='store_true',
            help='Skip registration test and only test emails with existing user',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 STARTING PRODUCTION SYSTEM TEST')
        )
        self.stdout.write("=" * 60)
        
        # Detect environment
        environment = 'PRODUCTION' if not settings.DEBUG else 'LOCAL'
        self.stdout.write(f"Environment: {environment}")
        self.stdout.write(f"Debug Mode: {settings.DEBUG}")
        self.stdout.write(f"Allowed Hosts: {settings.ALLOWED_HOSTS}")
        self.stdout.write("=" * 60)
        
        # Test basic setup
        if not self.test_basic_setup():
            return
        
        if options['skip_registration']:
            # Just test emails with existing user
            self.test_existing_user_emails(options['email'])
        else:
            # Test full registration flow
            self.test_registration_flow(options['email'])
    
    def test_basic_setup(self):
        """Test basic system setup"""
        self.stdout.write("\n🔧 TESTING BASIC SETUP")
        self.stdout.write("=" * 30)
        
        try:
            # Test database
            user_count = User.objects.count()
            self.stdout.write(
                self.style.SUCCESS(f"✅ Database: {user_count} users found")
            )
            
            # Test email settings
            email_settings = {
                'EMAIL_HOST': getattr(settings, 'EMAIL_HOST', 'NOT SET'),
                'EMAIL_HOST_USER': getattr(settings, 'EMAIL_HOST_USER', 'NOT SET'),
                'DEFAULT_FROM_EMAIL': getattr(settings, 'DEFAULT_FROM_EMAIL', 'NOT SET'),
            }
            
            missing = [k for k, v in email_settings.items() if v == 'NOT SET']
            if missing:
                self.stdout.write(
                    self.style.ERROR(f"❌ Missing email settings: {missing}")
                )
                return False
            else:
                self.stdout.write(
                    self.style.SUCCESS("✅ Email configuration complete")
                )
            
            # Test Redis
            try:
                import redis
                redis_url = getattr(settings, 'REDIS_URL', settings.CELERY_BROKER_URL)
                r = redis.from_url(redis_url)
                r.ping()
                self.stdout.write(
                    self.style.SUCCESS("✅ Redis connection successful")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"⚠️ Redis issue: {str(e)}")
                )
            
            return True
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Basic setup failed: {str(e)}")
            )
            return False
    
    def test_existing_user_emails(self, email=None):
        """Test email system with existing user"""
        self.stdout.write("\n📧 TESTING EMAIL SYSTEM")
        self.stdout.write("=" * 30)
        
        if email:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"❌ User with email {email} not found")
                )
                return
        else:
            user = User.objects.filter(is_active=True).first()
            if not user:
                self.stdout.write(
                    self.style.ERROR("❌ No active users found")
                )
                return
        
        self.stdout.write(f"Testing with user: {user.email}")
        
        try:
            # Test welcome email
            send_welcome_email.delay(user.id)
            self.stdout.write(
                self.style.SUCCESS("✅ Welcome email queued")
            )
            
            # Test verification email if user has verification record
            if hasattr(user, 'email_verification'):
                verification = user.email_verification
                send_verification_email.delay(user.id, verification.otp_code)
                self.stdout.write(
                    self.style.SUCCESS("✅ Verification email queued")
                )
            
            self.stdout.write(
                self.style.SUCCESS("📧 Check your email and Celery logs for delivery status")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Email test failed: {str(e)}")
            )
    
    def test_registration_flow(self, email=None):
        """Test complete registration flow"""
        self.stdout.write("\n👤 TESTING REGISTRATION FLOW")
        self.stdout.write("=" * 35)
        
        # Generate test email
        if not email:
            timestamp = int(time.time())
            email = f'production.test.{timestamp}@findnearbiz.com'
        
        # Clean up existing test user
        User.objects.filter(email=email).delete()
        
        # Test data
        test_data = {
            'username': f'prodtest_{int(time.time())}',
            'email': email,
            'first_name': 'Production',
            'last_name': 'Test',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'user_type': 'regular'
        }
        
        try:
            # Use Django's test client for form submission
            from accounts.forms import UserRegisterForm
            
            # Test form validation
            form = UserRegisterForm(test_data)
            if form.is_valid():
                self.stdout.write(
                    self.style.SUCCESS("✅ Registration form validation passed")
                )
                
                # Create user
                user = form.save(commit=False)
                user.is_active = False
                user.save()
                
                self.stdout.write(
                    self.style.SUCCESS(f"✅ User created: {user.username} ({user.email})")
                )
                
                # Check verification record
                if hasattr(user, 'email_verification'):
                    verification = user.email_verification
                    self.stdout.write(
                        self.style.SUCCESS("✅ Verification record created")
                    )
                    self.stdout.write(f"   OTP: {verification.otp_code}")
                    self.stdout.write(f"   Valid: {verification.is_otp_valid()}")
                    
                    # Test verification email
                    send_verification_email.delay(user.id, verification.otp_code)
                    self.stdout.write(
                        self.style.SUCCESS("✅ Verification email queued")
                    )
                    
                    # Simulate OTP verification
                    if verification.is_otp_valid():
                        user.is_active = True
                        user.save()
                        verification.is_verified = True
                        verification.save()
                        
                        self.stdout.write(
                            self.style.SUCCESS("✅ OTP verification simulated")
                        )
                        
                        # Test welcome email
                        send_welcome_email.delay(user.id)
                        self.stdout.write(
                            self.style.SUCCESS("✅ Welcome email queued")
                        )
                    
                else:
                    self.stdout.write(
                        self.style.ERROR("❌ No verification record created")
                    )
            else:
                self.stdout.write(
                    self.style.ERROR(f"❌ Form validation failed: {form.errors}")
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Registration test failed: {str(e)}")
            )
        
        # Final summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(
            self.style.SUCCESS("🎯 PRODUCTION TEST COMPLETED")
        )
        self.stdout.write("Check your email and DigitalOcean logs for email delivery.")
        self.stdout.write("=" * 60)