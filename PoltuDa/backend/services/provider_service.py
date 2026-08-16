import json
from datetime import datetime

from backend.extensions import db
from backend.models import Provider, Review, User


class ProviderService:
    @staticmethod
    def get_provider_profile(provider_id):
        provider = db.session.get(Provider, provider_id)
        if provider is None:
            return None

        data = provider.to_dict()
        reviews = Review.query.filter_by(provider_id=provider_id).order_by(Review.created_at.desc()).limit(10).all()
        data['recent_reviews'] = [review.to_dict() for review in reviews]
        data['offers'] = [offer.to_dict() for offer in provider.offers if hasattr(provider, 'offers')]
        return data

    @staticmethod
    def update_provider_profile(user, data):
        provider = user.provider_profile
        if provider is None:
            raise ValueError('Provider profile not found')

        if 'experience_years' in data:
            provider.experience_years = int(data['experience_years'])
        if 'hourly_rate' in data:
            provider.hourly_rate = float(data['hourly_rate'])
        if 'base_price' in data:
            provider.base_price = float(data['base_price'])
        if 'service_area_radius' in data:
            provider.service_area_radius = float(data['service_area_radius'])
        if 'availability_status' in data:
            provider.availability_status = str(data['availability_status'])
        if 'specializations' in data:
            provider.specializations = json.dumps(data['specializations'])
        if 'certifications' in data:
            provider.certifications = json.dumps(data['certifications'])
        if 'bio' in data:
            user.bio = str(data['bio']).strip()
        if 'phone' in data:
            user.phone = str(data['phone']).strip()

        provider.updated_at = datetime.utcnow()
        db.session.commit()
        return provider

    @staticmethod
    def add_review(customer, provider_id, payload):
        if customer.user_type != 'customer':
            raise PermissionError('Only customers can leave reviews')

        provider = db.session.get(Provider, provider_id)
        if provider is None:
            raise ValueError('Provider not found')

        rating = int(payload.get('rating'))
        if not 1 <= rating <= 5:
            raise ValueError('Rating must be between 1 and 5')

        existing_review = Review.query.filter_by(provider_id=provider_id, customer_id=customer.id).first()
        if existing_review:
            raise ValueError('You have already reviewed this provider')

        review = Review(
            provider_id=provider_id,
            customer_id=customer.id,
            rating=rating,
            title=(payload.get('title') or '').strip() or None,
            comment=(payload.get('comment') or '').strip() or None,
            is_verified_job=bool(payload.get('is_verified_job', False)),
        )

        db.session.add(review)
        db.session.flush()

        all_reviews = Review.query.filter_by(provider_id=provider_id).all()
        if all_reviews:
            avg_rating = sum(r.rating for r in all_reviews) / len(all_reviews)
            provider.rating = round(avg_rating, 2)
            provider.review_count = len(all_reviews)

        db.session.commit()
        return review
