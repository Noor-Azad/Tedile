"""
Services routes
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from backend.decorators import role_required

try:
    from .extensions import db
    from .models import Service, Provider, User
    from .services.service_catalog_service import ServiceCatalogService
except ImportError:  # pragma: no cover - fallback for script execution
    from extensions import db
    from models import Service, Provider, User
    from services.service_catalog_service import ServiceCatalogService

services_bp = Blueprint('services', __name__, url_prefix='/api/services')


@services_bp.route('', methods=['GET'])
def get_all_services():
    """Get all services"""
    page = max(1, request.args.get('page', 1, type=int))
    per_page = max(1, min(request.args.get('per_page', 20, type=int), 100))
    category = (request.args.get('category') or '').strip() or None
    search = (request.args.get('search') or '').strip()

    paginated = ServiceCatalogService.list_services(page=page, per_page=per_page, category=category, search=search)

    return jsonify({
        'services': [service.to_dict() for service in paginated.items],
        'total': paginated.total,
        'pages': paginated.pages,
        'current_page': page,
    }), 200


@services_bp.route('/<int:service_id>', methods=['GET'])
def get_service(service_id):
    """Get single service with provider count"""
    service_data = ServiceCatalogService.get_service_with_provider_count(service_id)
    if service_data is None:
        return jsonify({'error': 'Service not found'}), 404
    return jsonify(service_data), 200


@services_bp.route('/<int:service_id>/providers', methods=['GET'])
def get_service_providers(service_id):
    """Get all providers for a specific service"""
    service = db.session.get(Service, service_id)
    if not service:
        return jsonify({'error': 'Service not found'}), 404

    page = max(1, request.args.get('page', 1, type=int))
    per_page = max(1, min(request.args.get('per_page', 20, type=int), 100))
    city = (request.args.get('city') or '').strip() or None
    district = (request.args.get('district') or '').strip() or None
    min_rating = request.args.get('min_rating', type=float)
    sort_by = (request.args.get('sort_by', 'rating') or 'rating').strip().lower()

    query = Provider.query.filter_by(service_id=service_id).join(Provider.user).filter(
        db.and_(User.is_verified.is_(True), User.is_active.is_(True))
    )

    if city:
        query = query.filter(User.city.ilike(f'%{city}%'))
    if district:
        query = query.filter(User.district.ilike(f'%{district}%'))
    if min_rating is not None:
        query = query.filter(Provider.rating >= min_rating)

    if sort_by == 'rating':
        query = query.order_by(Provider.rating.desc())
    elif sort_by == 'experience':
        query = query.order_by(Provider.experience_years.desc())
    elif sort_by == 'price':
        query = query.order_by(Provider.hourly_rate.asc())

    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

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
    page = max(1, request.args.get('page', 1, type=int))
    per_page = max(1, min(request.args.get('per_page', 20, type=int), 100))

    if latitude is None or longitude is None:
        return jsonify({'error': 'Latitude and longitude are required'}), 400

    query = Provider.query.join(Provider.user).filter(
        User.is_verified.is_(True),
        User.is_active.is_(True),
        User.latitude.is_not(None),
        User.longitude.is_not(None),
    )

    if service_id:
        query = query.filter(Provider.service_id == service_id)

    providers = query.all()

    from math import radians, sin, cos, sqrt, atan2

    def haversine_distance(lat1, lon1, lat2, lon2):
        R = 6371
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return R * c

    nearby_providers = [
        p for p in providers
        if haversine_distance(latitude, longitude, p.user.latitude, p.user.longitude) <= radius
    ]

    nearby_providers.sort(
        key=lambda p: haversine_distance(latitude, longitude, p.user.latitude, p.user.longitude)
    )

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
            'radius': radius,
        },
    }), 200


@services_bp.route('', methods=['POST'])
@jwt_required()
@role_required('admin')
def create_service():
    """Create new service (admin only)"""
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)

    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid JSON payload'}), 400

    if not data.get('name'):
        return jsonify({'error': 'Service name is required'}), 400

    service = Service(
        name=str(data['name']).strip(),
        description=(data.get('description') or '').strip() or None,
        icon=(data.get('icon') or '').strip() or None,
        category=(data.get('category') or '').strip() or None,
    )

    try:
        db.session.add(service)
        db.session.commit()
        return jsonify({
            'message': 'Service created successfully',
            'service': service.to_dict(),
        }), 201
    except Exception as exc:
        db.session.rollback()
        return jsonify({'error': str(exc)}), 500


