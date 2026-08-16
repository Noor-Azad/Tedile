"""
Services routes
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Service, Provider, Review
from sqlalchemy import func

services_bp = Blueprint('services', __name__, url_prefix='/api/services')


@services_bp.route('', methods=['GET'])
def get_all_services():
    """Get all services"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    category = request.args.get('category')
    search = request.args.get('search')
    
    query = Service.query.filter_by(is_active=True)
    
    if category:
        query = query.filter_by(category=category)
    
    if search:
        query = query.filter(Service.name.ilike(f'%{search}%'))
    
    paginated = query.paginate(page=page, per_page=per_page)
    
    return jsonify({
        'services': [service.to_dict() for service in paginated.items],
        'total': paginated.total,
        'pages': paginated.pages,
        'current_page': page,
    }), 200


@services_bp.route('/<int:service_id>', methods=['GET'])
def get_service(service_id):
    """Get single service with provider count"""
    service = Service.query.get(service_id)
    
    if not service:
        return jsonify({'error': 'Service not found'}), 404
    
    service_data = service.to_dict()
    service_data['provider_count'] = Provider.query.filter_by(
        service_id=service_id,
    ).count()
    
    return jsonify(service_data), 200


@services_bp.route('/<int:service_id>/providers', methods=['GET'])
def get_service_providers(service_id):
    """Get all providers for a specific service"""
    service = Service.query.get(service_id)
    
    if not service:
        return jsonify({'error': 'Service not found'}), 404
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    city = request.args.get('city')
    district = request.args.get('district')
    min_rating = request.args.get('min_rating', type=float)
    sort_by = request.args.get('sort_by', 'rating')  # rating, experience, price
    
    query = Provider.query.filter_by(
        service_id=service_id,
    ).join(Provider.user).filter(
        db.and_(
            User.is_verified == True,
            User.is_active == True
        )
    )
    
    if city:
        from models import User
        query = query.filter(User.city.ilike(f'%{city}%'))
    
    if district:
        from models import User
        query = query.filter(User.district.ilike(f'%{district}%'))
    
    if min_rating:
        query = query.filter(Provider.rating >= min_rating)
    
    # Sort
    if sort_by == 'rating':
        query = query.order_by(Provider.rating.desc())
    elif sort_by == 'experience':
        query = query.order_by(Provider.experience_years.desc())
    elif sort_by == 'price':
        query = query.order_by(Provider.hourly_rate.asc())
    
    paginated = query.paginate(page=page, per_page=per_page)
    
    return jsonify({
        'service': service.to_dict(),
        'providers': [provider.to_dict() for provider in paginated.items],
        'total': paginated.total,
        'pages': paginated.pages,
        'current_page': page,
    }), 200


@services_bp.route('/search/by-location', methods=['GET'])
def search_by_location():
    """Search providers by location and service"""
    latitude = request.args.get('latitude', type=float)
    longitude = request.args.get('longitude', type=float)
    service_id = request.args.get('service_id', type=int)
    radius = request.args.get('radius', 10, type=float)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    if not latitude or not longitude:
        return jsonify({'error': 'Latitude and longitude are required'}), 400
    
    from models import User
    
    # Basic distance calculation (Haversine formula)
    # In production, use PostGIS for better performance
    
    query = Provider.query.join(Provider.user).filter(
        User.is_verified == True,
        User.is_active == True,
        User.latitude != None,
        User.longitude != None
    )
    
    if service_id:
        query = query.filter(Provider.service_id == service_id)
    
    providers = query.all()
    
    # Filter by distance
    from math import radians, sin, cos, sqrt, atan2
    
    def haversine_distance(lat1, lon1, lat2, lon2):
        R = 6371  # Earth radius in km
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c
    
    nearby_providers = [
        p for p in providers
        if haversine_distance(latitude, longitude, p.user.latitude, p.user.longitude) <= radius
    ]
    
    # Sort by distance
    nearby_providers.sort(
        key=lambda p: haversine_distance(latitude, longitude, p.user.latitude, p.user.longitude)
    )
    
    # Paginate
    start = (page - 1) * per_page
    end = start + per_page
    paginated_providers = nearby_providers[start:end]
    
    return jsonify({
        'providers': [provider.to_dict() for provider in paginated_providers],
        'total': len(nearby_providers),
        'pages': (len(nearby_providers) + per_page - 1) // per_page,
        'current_page': page,
        'search_location': {
            'latitude': latitude,
            'longitude': longitude,
            'radius': radius
        }
    }), 200


# Admin routes for managing services
@services_bp.route('', methods=['POST'])
@jwt_required()
def create_service():
    """Create new service (admin only)"""
    user_id = get_jwt_identity()
    from models import User
    user = User.query.get(user_id)
    
    # Check if admin (in production, use role-based access control)
    if not user or user.user_type != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    if not data.get('name'):
        return jsonify({'error': 'Service name is required'}), 400
    
    service = Service(
        name=data['name'],
        description=data.get('description'),
        icon=data.get('icon'),
        category=data.get('category'),
    )
    
    try:
        db.session.add(service)
        db.session.commit()
        return jsonify({
            'message': 'Service created successfully',
            'service': service.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# Import User for the search route
from models import User
