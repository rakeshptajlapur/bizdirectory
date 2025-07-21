import os
import django
from datetime import datetime, timedelta
import random

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import Profile
from directory.models import Category, Business, BusinessHours, Service, Review
from django.db import connection

def reset_database_completely():
    print("🔥 NUCLEAR RESET: Clearing everything and resetting sequences...")
    
    # Delete all data
    Review.objects.all().delete()
    Service.objects.all().delete()
    BusinessHours.objects.all().delete()
    Business.objects.all().delete()
    Category.objects.all().delete()
    Profile.objects.all().delete()
    User.objects.all().delete()
    
    # Reset all sequences to start from 1
    with connection.cursor() as cursor:
        tables_to_reset = [
            'auth_user',
            'accounts_profile', 
            'directory_category',
            'directory_business',
            'directory_businesshours',
            'directory_service',
            'directory_review'
        ]
        
        for table in tables_to_reset:
            try:
                cursor.execute(f"ALTER SEQUENCE {table}_id_seq RESTART WITH 1;")
                print(f"✅ Reset sequence for {table}")
            except Exception as e:
                print(f"⚠️  Could not reset {table}: {e}")
    
    print("🧨 Database completely reset!")

def create_demo_data():
    print("🚀 Creating fresh demo data...")
    
    # Create categories
    categories_data = [
        {'name': 'Restaurants & Food', 'slug': 'restaurants-food', 'description': 'Fine dining, cafes, food delivery'},
        {'name': 'Healthcare & Medical', 'slug': 'healthcare-medical', 'description': 'Hospitals, clinics, specialists'},
        {'name': 'Education & Training', 'slug': 'education-training', 'description': 'Schools, coaching, training'},
        {'name': 'Home Services', 'slug': 'home-services', 'description': 'Plumbing, electrical, cleaning'},
        {'name': 'Technology & IT', 'slug': 'technology-it', 'description': 'Software, IT support, web design'}
    ]
    
    categories = {}
    for cat_data in categories_data:
        category = Category.objects.create(**cat_data)
        categories[cat_data['slug']] = category
        print(f"✅ Created category: {category.name}")
    
    # Create admin user first
    admin_user = User.objects.create_superuser(
        username='admin',
        email='admin@bizdirectory.com', 
        password='admin123',
        first_name='Admin',
        last_name='User'
    )
    # UPDATE the profile instead of creating it
    admin_user.profile.user_type = 'business_owner'
    admin_user.profile.phone = '9999999999'
    admin_user.profile.save()
    print("✅ Created admin user")
    
    # Create business owners
    business_owners = []
    owner_names = [
        ('rajesh_kumar', 'Rajesh', 'Kumar'),
        ('priya_sharma', 'Priya', 'Sharma'),
        ('amit_patel', 'Amit', 'Patel'),
        ('sneha_gupta', 'Sneha', 'Gupta'),
        ('vikram_singh', 'Vikram', 'Singh'),
        ('anita_reddy', 'Anita', 'Reddy'),
        ('rahul_mehta', 'Rahul', 'Mehta'),
        ('kavya_joshi', 'Kavya', 'Joshi'),
        ('suresh_nair', 'Suresh', 'Nair'),
        ('deepika_rao', 'Deepika', 'Rao'),
        ('arjun_verma', 'Arjun', 'Verma'),
        ('meera_iyer', 'Meera', 'Iyer'),
        ('karan_bhatia', 'Karan', 'Bhatia'),
        ('pooja_agarwal', 'Pooja', 'Agarwal'),
        ('rohit_malhotra', 'Rohit', 'Malhotra'),
        ('shruti_desai', 'Shruti', 'Desai'),
        ('manish_kapoor', 'Manish', 'Kapoor'),
        ('ritu_saxena', 'Ritu', 'Saxena'),
        ('gaurav_mishra', 'Gaurav', 'Mishra'),
        ('swati_pandey', 'Swati', 'Pandey')
    ]
    
    for username, first_name, last_name in owner_names:
        user = User.objects.create_user(
            username=username,
            password='demo123',
            first_name=first_name,
            last_name=last_name,
            email=f"{username}@example.com"
        )
        # UPDATE the profile instead of creating it
        user.profile.user_type = 'business_owner'
        user.profile.phone = f"98765{random.randint(10000, 99999)}"
        user.profile.save()
        business_owners.append(user)
        print(f"✅ Created business owner: {user.get_full_name()}")
    
    # Create regular users
    regular_users = []
    customer_names = [
        ('customer1', 'Ramesh', 'Chandra'),
        ('customer2', 'Sunita', 'Devi'),
        ('customer3', 'Anil', 'Yadav'),
        ('customer4', 'Geeta', 'Kumari'),
        ('customer5', 'Manoj', 'Tiwari')
    ]
    
    for username, first_name, last_name in customer_names:
        user = User.objects.create_user(
            username=username,
            password='demo123',
            first_name=first_name,
            last_name=last_name,
            email=f"{username}@gmail.com"
        )
        # UPDATE the profile instead of creating it
        user.profile.user_type = 'regular'
        user.profile.phone = f"87654{random.randint(10000, 99999)}"
        user.profile.save()
        regular_users.append(user)
        print(f"✅ Created customer: {user.get_full_name()}")
    
    # Create 4 businesses per category
    business_templates = {
        'restaurants-food': [
            ('Royal Spice Restaurant', 'Authentic North Indian cuisine with traditional flavors'),
            ('Green Leaf Cafe', 'Healthy organic food cafe specializing in salads and smoothies'),
            ('Pizza Corner Express', 'Fast food chain specializing in wood-fired pizzas'),
            ('Traditional Sweets House', 'Premium quality Indian sweets and snacks')
        ],
        'healthcare-medical': [
            ('City Care Hospital', '200-bed multi-specialty hospital with 24/7 emergency services'),
            ('Wellness Dental Clinic', 'Modern dental clinic with advanced equipment'),
            ('Prime Diagnostic Center', 'State-of-the-art diagnostic center offering health checkups'),
            ('Ayurvedic Healing Center', 'Traditional Ayurvedic treatment center')
        ],
        'education-training': [
            ('Excellence Academy', 'Premier coaching institute for competitive exams'),
            ('TechSkills Institute', 'Professional IT training institute'),
            ('Little Stars Preschool', 'Nurturing preschool focusing on early childhood development'),
            ('Music & Arts Academy', 'Comprehensive music and arts education')
        ],
        'home-services': [
            ('QuickFix Home Services', 'Professional home repair and maintenance services'),
            ('CleanPro Cleaning Services', 'Professional cleaning services for homes and offices'),
            ('GreenThumb Gardening', 'Complete gardening and landscaping services'),
            ('SecureHome Security Systems', 'Advanced home security solutions')
        ],
        'technology-it': [
            ('Digital Solutions Hub', 'Full-service digital agency offering web development'),
            ('CloudTech IT Services', 'Enterprise IT solutions including cloud migration'),
            ('CodeCraft Software Studio', 'Custom software development company'),
            ('DataViz Analytics', 'Data analytics and business intelligence company')
        ]
    }
    
    business_count = 0
    owner_index = 0
    
    for category_slug, business_list in business_templates.items():
        category = categories[category_slug]
        
        for name, description in business_list:
            business = Business.objects.create(
                owner=business_owners[owner_index],
                category=category,
                name=name,
                description=description,
                address=f"{random.randint(1, 999)}, Main Road, Commercial Area",
                pincode=f"5600{random.randint(10, 99)}",
                city='Bangalore',
                phone=f"987654{random.randint(1000, 9999)}",
                email=f"info@{name.lower().replace(' ', '').replace('&', '')}.com",
                website=f"https://{name.lower().replace(' ', '').replace('&', '')}.com",
                registration_number=f"REG{random.randint(100000, 999999)}",
                # FIX: Make GST number exactly 15 characters
                gst_number = f"29ABCDE{random.randint(1000, 9999)}F{random.randint(1, 9)}Z{random.randint(1, 9)}",
                gst_verified=random.choice([True, False]),
                kyc_status=random.choice(['completed', 'pending']),
                is_active=True,
                is_approved=True
            )
            
            # Create business hours
            for day in range(1, 8):
                if day == 7:  # Sunday
                    BusinessHours.objects.create(
                        business=business, day=day, open_time='00:00', 
                        close_time='00:00', is_closed=True
                    )
                else:
                    BusinessHours.objects.create(
                        business=business, day=day, open_time='09:00',
                        close_time='18:00', is_closed=False
                    )
            
            # Create services
            service_names = ['Service 1', 'Service 2', 'Service 3']
            for service_name in service_names:
                Service.objects.create(
                    business=business,
                    name=f"{service_name} for {name}",
                    description=f"Professional {service_name.lower()} provided by {name}"
                )
            
            # Create reviews
            for i in range(random.randint(2, 4)):
                user = random.choice(regular_users)
                Review.objects.create(
                    business=business,
                    user=user,
                    name=user.get_full_name(),
                    email=user.email,
                    rating=random.randint(4, 5),
                    comment="Great service! Highly recommended.",
                    is_approved=True
                )
            
            business_count += 1
            owner_index += 1
            print(f"✅ Created business: {business.name}")
    
    print(f"\n🎉 SUCCESS! Created:")
    print(f"   - 5 categories")
    print(f"   - {business_count} businesses") 
    print(f"   - {len(business_owners)} business owners")
    print(f"   - {len(regular_users)} regular users")
    print(f"   - Business hours and services")
    print(f"   - Customer reviews")
    print(f"\n🔐 Login credentials:")
    print(f"   - Admin: admin / admin123")
    print(f"   - Business owners: [username] / demo123")
    print(f"   - Customers: customer1-5 / demo123")

if __name__ == "__main__":
    reset_database_completely()
    create_demo_data()