"""
Database Models for PoltuDa.in
"""
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

db = SQLAlchemy()


class User(db.Model):
    """User model for both customers and service providers"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # 'customer' or 'provider'
    city = db.Column(db.String(100), nullable=True)
    district = db.Column(db.String(100), nullable=True)
    area = db.Column(db.String(100), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    profile_picture = db.Column(db.String(255), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    provider_profile = db.relationship('Provider', uselist=False, back_populates='user')
    reviews_given = db.relationship('Review', foreign_keys='Review.customer_id', back_populates='customer')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'user_type': self.user_type,
            'city': self.city,
            'district': self.district,
            'area': self.area,
            'profile_picture': self.profile_picture,
            'bio': self.bio,
            'is_verified': self.is_verified,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Service(db.Model):
    """Service categories"""
    __tablename__ = 'services'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(255), nullable=True)
    category = db.Column(db.String(50), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    providers = db.relationship('Provider', back_populates='service')
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'icon': self.icon,
            'category': self.category,
            'is_active': self.is_active,
        }


class Provider(db.Model):
    """Service provider profile"""
    __tablename__ = 'providers'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False, index=True)
    experience_years = db.Column(db.Integer, default=0)
    hourly_rate = db.Column(db.Float, nullable=True)
    base_price = db.Column(db.Float, nullable=True)
    rating = db.Column(db.Float, default=0)
    review_count = db.Column(db.Integer, default=0)
    service_area_radius = db.Column(db.Float, default=10)  # in km
    availability_status = db.Column(db.String(20), default='available')  # available, busy, unavailable
    verification_status = db.Column(db.String(20), default='pending')  # pending, verified, rejected
    specializations = db.Column(db.Text, nullable=True)  # JSON string
    certifications = db.Column(db.Text, nullable=True)  # JSON string
    portfolio_images = db.Column(db.Text, nullable=True)  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='provider_profile')
    service = db.relationship('Service', back_populates='providers')
    reviews = db.relationship('Review', back_populates='provider', cascade='all, delete-orphan')
    jobs = db.relationship('Job', back_populates='provider', cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'service_id': self.service_id,
            'service_name': self.service.name if self.service else None,
            'user': self.user.to_dict() if self.user else None,
            'experience_years': self.experience_years,
            'hourly_rate': self.hourly_rate,
            'base_price': self.base_price,
            'rating': self.rating,
            'review_count': self.review_count,
            'service_area_radius': self.service_area_radius,
            'availability_status': self.availability_status,
            'verification_status': self.verification_status,
            'specializations': json.loads(self.specializations) if self.specializations else [],
            'certifications': json.loads(self.certifications) if self.certifications else [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Review(db.Model):
    """Review and rating for providers"""
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('providers.id'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=True)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    title = db.Column(db.String(200), nullable=True)
    comment = db.Column(db.Text, nullable=True)
    is_verified_job = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    provider = db.relationship('Provider', back_populates='reviews')
    customer = db.relationship('User', foreign_keys=[customer_id], back_populates='reviews_given')
    job = db.relationship('Job', back_populates='review')
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'provider_id': self.provider_id,
            'customer_id': self.customer_id,
            'customer_name': self.customer.first_name + ' ' + self.customer.last_name if self.customer else None,
            'rating': self.rating,
            'title': self.title,
            'comment': self.comment,
            'is_verified_job': self.is_verified_job,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Job(db.Model):
    """Job posting or service request"""
    __tablename__ = 'jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('providers.id'), nullable=True, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='open')  # open, assigned, in_progress, completed, cancelled
    budget = db.Column(db.Float, nullable=True)
    preferred_date = db.Column(db.DateTime, nullable=True)
    location = db.Column(db.String(255), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    images = db.Column(db.Text, nullable=True)  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    provider = db.relationship('Provider', back_populates='jobs')
    review = db.relationship('Review', uselist=False, back_populates='job')
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'provider_id': self.provider_id,
            'service_id': self.service_id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'budget': self.budget,
            'preferred_date': self.preferred_date.isoformat() if self.preferred_date else None,
            'location': self.location,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Offer(db.Model):
    """Special offers and deals from providers"""
    __tablename__ = 'offers'
    
    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('providers.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    discount_percentage = db.Column(db.Float, nullable=True)
    discount_amount = db.Column(db.Float, nullable=True)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'provider_id': self.provider_id,
            'title': self.title,
            'description': self.description,
            'discount_percentage': self.discount_percentage,
            'discount_amount': self.discount_amount,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class BlogPost(db.Model):
    """Blog posts and tips"""
    __tablename__ = 'blog_posts'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    slug = db.Column(db.String(300), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=True)
    featured_image = db.Column(db.String(255), nullable=True)
    author = db.Column(db.String(100), nullable=True)
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'content': self.content,
            'category': self.category,
            'featured_image': self.featured_image,
            'author': self.author,
            'is_published': self.is_published,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
