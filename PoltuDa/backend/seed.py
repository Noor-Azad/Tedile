"""
Database seeding script
Populate initial data for development and testing
"""
from app import app, db
from models import User, Service, Provider, Offer, BlogPost
from datetime import datetime, timedelta
import json


def seed_database():
    """Seed the database with initial data"""
    
    with app.app_context():
        # Clear existing data
        print("Clearing existing data...")
        db.drop_all()
        db.create_all()
        
        # Seed services
        print("Seeding services...")
        services_data = [
            {
                'name': 'Plumber',
                'description': 'Professional plumbing services including leak repairs, pipe fitting, and installations',
                'icon': '🔧',
                'category': 'Home Repair'
            },
            {
                'name': 'Electrician',
                'description': 'Electrical wiring, repairs, installations, and safety inspections',
                'icon': '⚡',
                'category': 'Home Repair'
            },
            {
                'name': 'Carpenter',
                'description': 'Furniture repair, custom woodwork, and wooden installations',
                'icon': '🪵',
                'category': 'Home Repair'
            },
            {
                'name': 'Painter',
                'description': 'Interior and exterior painting with premium quality finishes',
                'icon': '🎨',
                'category': 'Home Repair'
            },
            {
                'name': 'Welder',
                'description': 'Metal fabrication, gate repairs, grills, and structural welding',
                'icon': '🔥',
                'category': 'Home Repair'
            },
            {
                'name': 'AC Repair',
                'description': 'AC installation, repair, gas refilling, and maintenance',
                'icon': '❄️',
                'category': 'Home Repair'
            },
            {
                'name': 'Cleaning',
                'description': 'Professional cleaning services for homes and offices',
                'icon': '🧹',
                'category': 'Home Services'
            },
            {
                'name': 'Interior Designer',
                'description': 'Interior design and home decoration services',
                'icon': '🏠',
                'category': 'Home Services'
            },
            {
                'name': 'Tuition Teacher',
                'description': 'Home tuition and educational services',
                'icon': '📚',
                'category': 'Education'
            },
            {
                'name': 'Solar Panel Setup',
                'description': 'Solar panel installation and maintenance',
                'icon': '☀️',
                'category': 'Home Services'
            },
        ]
        
        services = []
        for service_data in services_data:
            service = Service(**service_data)
            services.append(service)
            db.session.add(service)
        
        db.session.commit()
        print(f"✅ Created {len(services)} services")
        
        # Seed demo users (customers and providers)
        print("\nSeeding users and providers...")
        
        # Create demo customers
        customers_data = [
            {
                'email': 'customer1@example.com',
                'password': 'password123',
                'first_name': 'Rajesh',
                'last_name': 'Kumar',
                'phone': '9876543210',
                'city': 'Malda',
                'district': 'Malda',
                'area': 'Town',
                'latitude': 25.9833,
                'longitude': 88.6167
            },
            {
                'email': 'customer2@example.com',
                'password': 'password123',
                'first_name': 'Priya',
                'last_name': 'Singh',
                'phone': '8765432109',
                'city': 'Siliguri',
                'district': 'Darjeeling',
                'area': 'Hakimpara',
                'latitude': 26.7271,
                'longitude': 88.4029
            },
        ]
        
        customers = []
        for customer_data in customers_data:
            password = customer_data.pop('password')
            customer = User(user_type='customer', **customer_data)
            customer.set_password(password)
            customers.append(customer)
            db.session.add(customer)
        
        db.session.commit()
        print(f"✅ Created {len(customers)} customers")
        
        # Create demo providers
        print("\nSeeding providers...")
        providers_data = [
            {
                'email': 'plumber1@example.com',
                'password': 'password123',
                'first_name': 'Mohan',
                'last_name': 'Sharma',
                'phone': '9123456789',
                'city': 'Malda',
                'district': 'Malda',
                'area': 'Town',
                'latitude': 25.9833,
                'longitude': 88.6167,
                'bio': 'Expert plumber with 10 years of experience',
                'service_id': 1,  # Plumber
                'experience_years': 10,
                'hourly_rate': 300,
                'base_price': 500,
                'rating': 4.8,
                'review_count': 15
            },
            {
                'email': 'electrician1@example.com',
                'password': 'password123',
                'first_name': 'Rajesh',
                'last_name': 'Patel',
                'phone': '8765432108',
                'city': 'Malda',
                'district': 'Malda',
                'area': 'Market',
                'latitude': 25.9820,
                'longitude': 88.6180,
                'bio': 'Licensed electrician, emergency services available',
                'service_id': 2,  # Electrician
                'experience_years': 8,
                'hourly_rate': 250,
                'base_price': 400,
                'rating': 4.7,
                'review_count': 20
            },
            {
                'email': 'carpenter1@example.com',
                'password': 'password123',
                'first_name': 'Vikram',
                'last_name': 'Singh',
                'phone': '7654321098',
                'city': 'Siliguri',
                'district': 'Darjeeling',
                'area': 'Hakimpara',
                'latitude': 26.7271,
                'longitude': 88.4029,
                'bio': 'Custom woodwork and furniture specialist',
                'service_id': 3,  # Carpenter
                'experience_years': 12,
                'hourly_rate': 350,
                'base_price': 600,
                'rating': 4.9,
                'review_count': 25
            },
            {
                'email': 'painter1@example.com',
                'password': 'password123',
                'first_name': 'Arjun',
                'last_name': 'Kumar',
                'phone': '6543210987',
                'city': 'Balurghat',
                'district': 'South Dinajpur',
                'area': 'Main Bazaar',
                'latitude': 25.2232,
                'longitude': 88.8000,
                'bio': 'Professional painter with modern techniques',
                'service_id': 4,  # Painter
                'experience_years': 6,
                'hourly_rate': 200,
                'base_price': 350,
                'rating': 4.6,
                'review_count': 18
            },
            {
                'email': 'acrepair1@example.com',
                'password': 'password123',
                'first_name': 'Deepak',
                'last_name': 'Tiwari',
                'phone': '5432109876',
                'city': 'Raiganj',
                'district': 'Uttar Dinajpur',
                'area': 'Town',
                'latitude': 25.6001,
                'longitude': 87.9131,
                'bio': 'AC and refrigerator repair specialist',
                'service_id': 6,  # AC Repair
                'experience_years': 9,
                'hourly_rate': 400,
                'base_price': 800,
                'rating': 4.8,
                'review_count': 22
            },
        ]
        
        providers = []
        for provider_data in providers_data:
            password = provider_data.pop('password')
            service_id = provider_data.pop('service_id')
            experience = provider_data.pop('experience_years')
            hourly_rate = provider_data.pop('hourly_rate')
            base_price = provider_data.pop('base_price')
            rating = provider_data.pop('rating')
            review_count = provider_data.pop('review_count')
            
            provider_user = User(user_type='provider', is_verified=True, **provider_data)
            provider_user.set_password(password)
            db.session.add(provider_user)
            db.session.flush()
            
            provider = Provider(
                user_id=provider_user.id,
                service_id=service_id,
                experience_years=experience,
                hourly_rate=hourly_rate,
                base_price=base_price,
                rating=rating,
                review_count=review_count,
                verification_status='verified',
                specializations=json.dumps(['Repair', 'Installation', 'Maintenance']),
                certifications=json.dumps(['Certified', 'Experienced']),
            )
            providers.append(provider)
            db.session.add(provider)
        
        db.session.commit()
        print(f"✅ Created {len(providers)} providers")
        
        # Create demo offers
        print("\nSeeding offers...")
        offers_data = [
            {
                'provider_id': 1,
                'title': '20% Discount on Water Pipe Installation',
                'description': 'Special offer on new water pipe installation',
                'discount_percentage': 20,
                'start_date': datetime.utcnow(),
                'end_date': datetime.utcnow() + timedelta(days=30)
            },
            {
                'provider_id': 2,
                'title': 'Free Electrical Inspection',
                'description': 'Get a free home electrical inspection',
                'discount_amount': 500,
                'start_date': datetime.utcnow(),
                'end_date': datetime.utcnow() + timedelta(days=15)
            },
            {
                'provider_id': 3,
                'title': 'Custom Furniture - 15% Off',
                'description': 'Discount on custom furniture orders',
                'discount_percentage': 15,
                'start_date': datetime.utcnow(),
                'end_date': datetime.utcnow() + timedelta(days=45)
            },
        ]
        
        for offer_data in offers_data:
            offer = Offer(**offer_data)
            db.session.add(offer)
        
        db.session.commit()
        print(f"✅ Created {len(offers_data)} offers")
        
        # Create demo blog posts
        print("\nSeeding blog posts...")
        blog_posts_data = [
            {
                'title': 'Why Your Water Pressure is Low - Quick Fix Guide',
                'slug': 'low-water-pressure-fix',
                'content': 'Low water pressure can be caused by several factors... Common solutions include checking the main valve, cleaning aerators...',
                'category': 'Plumbing',
                'author': 'PoltuDa Team',
                'is_published': True
            },
            {
                'title': 'Electrical Safety Tips for Your Home',
                'slug': 'electrical-safety-tips',
                'content': 'Electrical safety is crucial for every household. Here are key tips to keep your home safe...',
                'category': 'Electrical',
                'author': 'Safety Expert',
                'is_published': True
            },
            {
                'title': 'Latest Paint Trends for 2024',
                'slug': 'paint-trends-2024',
                'content': 'Discover the hottest paint colors and finishes for 2024. From bold colors to subtle pastels...',
                'category': 'Painting',
                'author': 'Design Expert',
                'is_published': True
            },
        ]
        
        for blog_data in blog_posts_data:
            blog = BlogPost(**blog_data)
            db.session.add(blog)
        
        db.session.commit()
        print(f"✅ Created {len(blog_posts_data)} blog posts")
        
        print("\n✅ Database seeding completed successfully!")
        print("\nDemo Credentials:")
        print("Customer: customer1@example.com / password123")
        print("Provider: plumber1@example.com / password123")


if __name__ == '__main__':
    seed_database()
