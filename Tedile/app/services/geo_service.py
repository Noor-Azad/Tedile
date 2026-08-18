import math


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in kilometres."""
    earth_radius_km = 6371.0

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.asin(min(1, math.sqrt(a)))
    return earth_radius_km * c


def geocode_locality(query: str):
    """Look up a known city/locality by name in the local `locations` table.

    This is a lightweight stand-in for a third-party geocoding API and only
    resolves localities that have been seeded/added to the database.
    """
    from app.models.location import Location

    query = (query or "").strip()
    if not query:
        return None

    match = Location.query.filter(Location.city.ilike(f"%{query}%")).first()
    return match.to_dict() if match else None
