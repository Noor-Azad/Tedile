from sqlalchemy import func

from backend.extensions import db
from backend.models import Provider, Service, User


class ServiceCatalogService:
    @staticmethod
    def list_services(page=1, per_page=20, category=None, search=None):
        query = Service.query.filter_by(is_active=True)

        if category:
            query = query.filter(Service.category == category)

        if search:
            query = query.filter(Service.name.ilike(f'%{search}%'))

        return query.paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def get_service_with_provider_count(service_id):
        service = db.session.get(Service, service_id)
        if service is None:
            return None

        service_data = service.to_dict()
        service_data['provider_count'] = Provider.query.filter_by(service_id=service_id).count()
        return service_data

    @staticmethod
    def search_providers(filters):
        query = Provider.query.join(Provider.user).filter(
            User.is_verified.is_(True),
            User.is_active.is_(True),
        )

        if filters.get('service_id') is not None:
            query = query.filter(Provider.service_id == int(filters['service_id']))
        if filters.get('city'):
            query = query.filter(User.city.ilike(f"%{filters['city']}%"))
        if filters.get('district'):
            query = query.filter(User.district.ilike(f"%{filters['district']}%"))
        if filters.get('area'):
            query = query.filter(User.area.ilike(f"%{filters['area']}%"))
        if filters.get('min_rating') is not None:
            query = query.filter(Provider.rating >= float(filters['min_rating']))
        if filters.get('min_experience') is not None:
            query = query.filter(Provider.experience_years >= int(filters['min_experience']))

        sort_by = filters.get('sort_by', 'rating')
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

        page = int(filters.get('page', 1))
        per_page = int(filters.get('per_page', 20))
        return query.paginate(page=page, per_page=per_page, error_out=False)
