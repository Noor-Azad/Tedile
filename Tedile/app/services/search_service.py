from app.extensions import db
from app.models.provider import Provider
from app.models.provider_service import ProviderService
from app.models.service import Service
from app.services.geo_service import haversine_km


def distance_bucket(distance_km):
    if distance_km is None:
        return "unknown"
    if distance_km < 5:
        return "under_5km"
    if distance_km < 10:
        return "5_10km"
    if distance_km < 25:
        return "10_25km"
    if distance_km < 50:
        return "25_50km"
    return "over_50km"


def search_providers(
    latitude: float = None,
    longitude: float = None,
    radius_km: float = 50,
    service_slug: str = None,
    keyword: str = None,
    min_price: float = None,
    max_price: float = None,
    verified_only: bool = False,
    sort: str = "distance",
    limit: int = None,
    offset: int = 0,
    return_meta: bool = False,
):
    """Search providers by service/location/price, mirroring a provider-search API."""
    query = (
        Provider.query
        .join(ProviderService, ProviderService.provider_id == Provider.id)
        .join(Service, Service.id == ProviderService.service_id)
        .filter(
            Provider.is_active.is_(True),
            ProviderService.is_active.is_(True),
            Service.is_active.is_(True),
        )
    )

    if service_slug:
        query = query.filter(Service.slug == service_slug)

    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            db.or_(
                Provider.first_name.ilike(like),
                Provider.last_name.ilike(like),
                Provider.city.ilike(like),
            )
        )

    if min_price is not None:
        query = query.filter(Provider.hourly_rate >= min_price)
    if max_price is not None:
        query = query.filter(Provider.hourly_rate <= max_price)
    if verified_only:
        query = query.filter(Provider.verified.is_(True))

    providers = query.all()

    results = []
    for provider in providers:
        distance_km = None
        if latitude is not None and longitude is not None and provider.latitude and provider.longitude:
            distance_km = haversine_km(latitude, longitude, provider.latitude, provider.longitude)
            if radius_km is not None and distance_km > radius_km:
                continue

        # Keep exact distance private; only the coarse bucket is public.
        record = provider.to_public_dto()
        record["_distance_km"] = distance_km
        results.append(record)

    sort_key_map = {
        "distance": lambda r: (r["_distance_km"] is None, r["_distance_km"] or 0),
        "rating-high": lambda r: -(r["rating"] or 0),
        "rating-low": lambda r: (r["rating"] or 0),
        "price-low": lambda r: (r["hourly_rate"] or 0),
        "price-high": lambda r: -(r["hourly_rate"] or 0),
        "experience": lambda r: -(r["experience_years"] or 0),
        "jobs": lambda r: -(r["jobs_completed"] or 0),
        "reviews": lambda r: -(r["reviews_count"] or 0),
        "name-asc": lambda r: (r["name"] or "").lower(),
        "name-desc": lambda r: (r["name"] or "").lower(),
    }
    key_fn = sort_key_map.get(sort, sort_key_map["distance"])
    results.sort(key=key_fn, reverse=(sort == "name-desc"))

    for record in results:
        record["distance_bucket"] = distance_bucket(record.pop("_distance_km"))

    total = len(results)
    if limit is not None:
        results = results[offset:offset + limit]
    elif offset:
        results = results[offset:]

    if return_meta:
        return results, total
    return results
