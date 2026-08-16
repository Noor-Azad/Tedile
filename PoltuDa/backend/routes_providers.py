"""
Provider routes
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Provider, Review, User, Service
from datetime import datetime
import json

providers_bp = Blueprint('providers', __name__, url_prefix='/api/providers')


@providers_bp.route('/<int:provider_id>', methods=['GET'])
def get_provider(provider_id):
    """Get provider profile with reviews and ratings"""
    provider = Provider.query.get(provider_id)
    
    if not provider:
        return jsonify({'error': 'Provider not found'}), 404
    
    provider_data = provider.to_dict()
    
    # Get reviews
    reviews = Review.query.filter_by(provider_id=provider_id).order_by(Review.created_at.desc()).limit(10).all()
    provider_data['recent_reviews'] = [review.to_dict() for review in reviews]
    
    # Get offers
    from models import Offer
    offers = Offer.query.filter_by(provider_id=provider_id, is_active=True).all()
    provider_data['offers'] = [offer.to_dict() for offer in offers]
    
    return jsonify(provider_data), 200


@providers_bp.route('/<int:provider_id>/reviews', methods=['GET'])
def get_provider_reviews(provider_id):
    """Get all reviews for a provider"""
    provider = Provider.query.get(provider_id)
    
    if not provider:
        return jsonify({'error': 'Provider not found'}), 404
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    min_rating = request.args.get('min_rating', type=int)
    
    query = Review.query.filter_by(provider_id=provider_id)
    
    if min_rating:
        query = query.filter(Review.rating >= min_rating)
    
    paginated = query.order_by(Review.created_at.desc()).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'provider_id': provider_id,
        'reviews': [review.to_dict() for review in paginated.items],
        'total': paginated.total,
        'pages': paginated.pages,
        'current_page': page,
        'average_rating': provider.rating,
    }), 200


@providers_bp.route('/me', methods=['GET'])
@jwt_required()
def get_my_profile():
    """Get current user's provider profile"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or user.user_type != 'provider':
        return jsonify({'error': 'User is not a provider'}), 403
    
    if not user.provider_profile:
        return jsonify({'error': 'Provider profile not found'}), 404
    
    provider_data = user.provider_profile.to_dict()
    
    # Get recent reviews
    reviews = Review.query.filter_by(provider_id=user.provider_profile.id).order_by(Review.created_at.desc()).limit(5).all()
    provider_data['recent_reviews'] = [review.to_dict() for review in reviews]
    
    return jsonify(provider_data), 200


@providers_bp.route('/me', methods=['PUT'])
@jwt_required()
def update_my_profile():
    """Update provider profile"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or user.user_type != 'provider':
        return jsonify({'error': 'User is not a provider'}), 403
    
    provider = user.provider_profile
    if not provider:
        return jsonify({'error': 'Provider profile not found'}), 404
    
    data = request.get_json()
    
    # Update provider fields
    if 'experience_years' in data:
        provider.experience_years = data['experience_years']
    if 'hourly_rate' in data:
        provider.hourly_rate = data['hourly_rate']
    if 'base_price' in data:
        provider.base_price = data['base_price']
    if 'service_area_radius' in data:
        provider.service_area_radius = data['service_area_radius']
    if 'availability_status' in data:
        provider.availability_status = data['availability_status']
    if 'specializations' in data:
        provider.specializations = json.dumps(data['specializations'])
    if 'certifications' in data:
        provider.certifications = json.dumps(data['certifications'])
    
    # Update user fields
    if 'bio' in data:
        user.bio = data['bio']
    if 'phone' in data:
        user.phone = data['phone']
    
    try:
        provider.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({
            'message': 'Profile updated successfully',
            'provider': provider.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@providers_bp.route('', methods=['GET'])
def search_providers():
    """Search providers by various filters"""
    service_id = request.args.get('service_id', type=int)
    city = request.args.get('city')
    district = request.args.get('district')
    area = request.args.get('area')
    min_rating = request.args.get('min_rating', type=float)
    min_experience = request.args.get('min_experience', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    sort_by = request.args.get('sort_by', 'rating')
    
    query = Provider.query.join(Provider.user).filter(
        User.is_verified == True,
        User.is_active == True
    )
    
    if service_id:
        query = query.filter(Provider.service_id == service_id)
    
    if city:
        query = query.filter(User.city.ilike(f'%{city}%'))
    
    if district:
        query = query.filter(User.district.ilike(f'%{district}%'))
    
    if area:
        query = query.filter(User.area.ilike(f'%{area}%'))
    
    if min_rating:
        query = query.filter(Provider.rating >= min_rating)
    
    if min_experience:
        query = query.filter(Provider.experience_years >= min_experience)
    
    # Sort
    if sort_by == 'rating':
        query = query.order_by(Provider.rating.desc())
    elif sort_by == 'experience':
        query = query.order_by(Provider.experience_years.desc())
    elif sort_by == 'recent':
        query = query.order_by(Provider.created_at.desc())
    elif sort_by == 'price_asc':
        query = query.order_by(Provider.hourly_rate.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(Provider.hourly_rate.desc())
    
    paginated = query.paginate(page=page, per_page=per_page)
    
    return jsonify({
        'providers': [provider.to_dict() for provider in paginated.items],
        'total': paginated.total,
        'pages': paginated.pages,
        'current_page': page,
    }), 200


@providers_bp.route('/<int:provider_id>/reviews', methods=['POST'])
@jwt_required()
def add_review(provider_id):
    """Add a review for a provider"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user or user.user_type != 'customer':
        return jsonify({'error': 'Only customers can leave reviews'}), 403
    
    provider = Provider.query.get(provider_id)
    if not provider:
        return jsonify({'error': 'Provider not found'}), 404
    
    data = request.get_json()
    
    if 'rating' not in data or not (1 <= data['rating'] <= 5):
        return jsonify({'error': 'Rating must be between 1 and 5'}), 400
    
    # Check if user already reviewed this provider
    existing_review = Review.query.filter_by(
        provider_id=provider_id,
        customer_id=user_id
    ).first()
    
    if existing_review:
        return jsonify({'error': 'You have already reviewed this provider'}), 409
    
    review = Review(
        provider_id=provider_id,
        customer_id=user_id,
        rating=data['rating'],
        title=data.get('title'),
        comment=data.get('comment'),
        is_verified_job=data.get('is_verified_job', False),
    )
    
    try:
        db.session.add(review)
        
        # Update provider rating
        all_reviews = Review.query.filter_by(provider_id=provider_id).all()
        if all_reviews:
            avg_rating = sum(r.rating for r in all_reviews) / len(all_reviews)
            provider.rating = round(avg_rating, 2)
            provider.review_count = len(all_reviews)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Review added successfully',
            'review': review.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@providers_bp.route('/<int:provider_id>/offers', methods=['GET'])
def get_provider_offers(provider_id):
    """Get all active offers for a provider"""
    from models import Offer
    from datetime import datetime as dt
    
    provider = Provider.query.get(provider_id)
    if not provider:
        return jsonify({'error': 'Provider not found'}), 404
    
    offers = Offer.query.filter_by(
        provider_id=provider_id,
        is_active=True
    ).filter(
        Offer.end_date >= dt.utcnow()
    ).all()
    
    return jsonify({
        'provider_id': provider_id,
        'offers': [offer.to_dict() for offer in offers]
    }), 200
