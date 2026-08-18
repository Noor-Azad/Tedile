import secrets
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request, session

from app.extensions import db
from app.models.provider_service import ProviderService
from app.models.service import Service
from app.models.provider import Provider
from app.models.user import User
from app.routes.customer import login_required
from app.security import csrf_protect
from app.services.geo_service import geocode_locality
from app.services.search_service import search_providers

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/search/geocode")
def geocode():
    query = request.args.get("q", "")
    match = geocode_locality(query)
    if not match:
        return jsonify({"status": False, "message": "Location not found", "data": []}), 404
    return jsonify({"status": True, "message": "Location found", "data": [match]})


@api_bp.route("/search/providers")
def search():
    def _float(name):
        value = request.args.get(name)
        return float(value) if value not in (None, "") else None

    latitude = _float("latitude")
    longitude = _float("longitude")
    radius = request.args.get("radius", type=float) or current_app.config.get("DEFAULT_SEARCH_RADIUS_KM", 50)
    limit = min(max(request.args.get("limit", type=int) or 20, 1), 50)
    offset = max(request.args.get("offset", type=int) or 0, 0)

    results, total = search_providers(
        latitude=latitude,
        longitude=longitude,
        radius_km=radius,
        service_slug=request.args.get("service"),
        keyword=request.args.get("keyword"),
        min_price=_float("min_price"),
        max_price=_float("max_price"),
        verified_only=request.args.get("verified_only") in ("1", "true", "True"),
        sort=request.args.get("sort", "distance"),
        limit=limit,
        offset=offset,
        return_meta=True,
    )

    next_offset = offset + limit if offset + limit < total else None
    return jsonify({
        "status": True,
        "message": "Providers found",
        "count": len(results),
        "total": total,
        "limit": limit,
        "offset": offset,
        "next_offset": next_offset,
        "data": {"providers": results},
    })


@api_bp.route("/providers/<profile_code>")
def provider_profile(profile_code):
    provider = Provider.query.filter_by(profile_code=profile_code).first()
    if not provider or not provider.is_active:
        return jsonify({"error": "Provider not found"}), 404
    has_active_service = (
        ProviderService.query
        .join(Service, Service.id == ProviderService.service_id)
        .filter(
            ProviderService.provider_id == provider.id,
            ProviderService.is_active.is_(True),
            Service.is_active.is_(True),
        )
        .first()
    )
    if not has_active_service:
        return jsonify({"error": "Provider not found"}), 404
    return jsonify(provider.to_public_dto())


@api_bp.route("/services")
def list_services():
    services = Service.query.order_by(Service.name.asc()).all()
    return jsonify({"status": True, "data": [s.to_public_dict() for s in services]})


def _payload():
    return request.get_json(silent=True) or request.form.to_dict()


def _authorized_provider(provider):
    user = session["user"]
    return user.get("role") == "admin" or (
        user.get("role") == "provider" and provider.user_id == user.get("id")
    )


def _provider_response(provider):
    if session["user"].get("role") == "admin":
        return provider.to_admin_dto()
    return provider.to_provider_owner_dto()


def _new_profile_code():
    while True:
        profile_code = f"TED-{secrets.token_urlsafe(9)}"
        if not Provider.query.filter_by(profile_code=profile_code).first():
            return profile_code


@api_bp.route("/providers", methods=["POST"])
@login_required()
@csrf_protect
def create_provider():
    user = session["user"]
    if user.get("role") not in {"provider", "admin"}:
        return jsonify({"error": "Only providers or admins can create provider profiles"}), 403

    payload = _payload()
    profile_code = _new_profile_code()

    owner_id = user["id"] if user.get("role") == "provider" else payload.get("user_id")
    if owner_id and not User.query.filter_by(id=owner_id, role="provider").first():
        return jsonify({"error": "Provider owner account not found"}), 400

    provider = Provider(
        profile_code=profile_code,
        user_id=owner_id,
        first_name=(payload.get("first_name") or payload.get("name") or "").strip(),
        last_name=(payload.get("last_name") or "").strip() or None,
        phone=payload.get("phone") or None,
        whatsapp=payload.get("whatsapp") or None,
        city=payload.get("city") or None,
        state=payload.get("state") or None,
        latitude=payload.get("latitude"),
        longitude=payload.get("longitude"),
        hourly_rate=payload.get("hourly_rate"),
        experience_years=payload.get("experience_years") or 0,
        availability=payload.get("availability") or "available",
        verified=False,
        is_active=True,
    )
    if not provider.first_name:
        return jsonify({"error": "first_name or name is required"}), 400

    db.session.add(provider)
    db.session.commit()
    return jsonify(_provider_response(provider)), 201


@api_bp.route("/providers/<profile_code>", methods=["PATCH"])
@login_required()
@csrf_protect
def update_provider(profile_code):
    provider = Provider.query.filter_by(profile_code=profile_code).first()
    if not provider:
        return jsonify({"error": "Provider not found"}), 404
    if not _authorized_provider(provider):
        return jsonify({"error": "You cannot modify this provider"}), 403

    payload = _payload()
    editable_fields = {
        "first_name", "last_name", "phone", "whatsapp", "city", "state",
        "latitude", "longitude", "hourly_rate", "experience_years",
        "availability", "profile_photo_url",
    }
    for field in editable_fields:
        if field in payload:
            setattr(provider, field, payload[field] or None)

    if session["user"].get("role") == "admin" and "verified" in payload:
        provider.verified = str(payload["verified"]).lower() in {"1", "true", "yes"}

    db.session.commit()
    return jsonify(_provider_response(provider))


@api_bp.route("/providers/<profile_code>/services", methods=["POST"])
@login_required()
@csrf_protect
def add_provider_service(profile_code):
    provider = Provider.query.filter_by(profile_code=profile_code).first()
    if not provider:
        return jsonify({"error": "Provider not found"}), 404
    if not _authorized_provider(provider):
        return jsonify({"error": "You cannot modify this provider"}), 403

    payload = _payload()
    service = Service.query.filter_by(slug=(payload.get("service_slug") or "").strip()).first()
    if not service:
        return jsonify({"error": "Service not found"}), 404

    relation = ProviderService.query.filter_by(
        provider_id=provider.id, service_id=service.id
    ).first()
    if relation:
        return jsonify({"created": False, "provider_profile_code": provider.profile_code, "service": service.to_public_dto()}), 200

    relation = ProviderService(provider_id=provider.id, service_id=service.id)
    relation.set_sub_services(payload.get("sub_services") or [])
    db.session.add(relation)
    db.session.commit()
    return jsonify({"created": True, "provider_profile_code": provider.profile_code, "service": service.to_public_dto()}), 201


@api_bp.route("/providers/<profile_code>/services/<service_slug>", methods=["DELETE"])
@login_required()
@csrf_protect
def remove_provider_service(profile_code, service_slug):
    provider = Provider.query.filter_by(profile_code=profile_code).first()
    if not provider:
        return jsonify({"error": "Provider not found"}), 404
    if not _authorized_provider(provider):
        return jsonify({"error": "You cannot modify this provider"}), 403

    service = Service.query.filter_by(slug=service_slug).first()
    relation = ProviderService.query.filter_by(
        provider_id=provider.id,
        service_id=service.id if service else None,
    ).first()
    if not relation:
        return jsonify({"error": "Provider service relationship not found"}), 404

    db.session.delete(relation)
    db.session.commit()
    return jsonify({"deleted": True, "provider_profile_code": provider.profile_code, "service_slug": service_slug})


def _admin_provider(profile_code):
    provider = Provider.query.filter_by(profile_code=profile_code).first()
    if not provider:
        return None, (jsonify({"error": "Provider not found"}), 404)
    return provider, None


@api_bp.route("/admin/providers", methods=["POST"])
@login_required(role="admin")
@csrf_protect
def admin_create_provider():
    payload = _payload()
    owner = None
    owner_email = (payload.get("owner_email") or "").strip().lower()
    if owner_email:
        owner = User.query.filter_by(email=owner_email, role="provider").first()
        if not owner:
            return jsonify({"error": "Provider owner account not found"}), 400

    first_name = (payload.get("first_name") or payload.get("name") or "").strip()
    if not first_name:
        return jsonify({"error": "first_name or name is required"}), 400

    provider = Provider(
        profile_code=_new_profile_code(),
        user_id=owner.id if owner else None,
        first_name=first_name,
        last_name=(payload.get("last_name") or "").strip() or None,
        phone=payload.get("phone") or None,
        whatsapp=payload.get("whatsapp") or None,
        city=payload.get("city") or None,
        state=payload.get("state") or None,
        latitude=payload.get("latitude"),
        longitude=payload.get("longitude"),
        hourly_rate=payload.get("hourly_rate"),
        experience_years=payload.get("experience_years") or 0,
        availability=payload.get("availability") or "available",
        verified=False,
        is_active=True,
    )
    db.session.add(provider)
    db.session.commit()
    return jsonify(provider.to_admin_dto()), 201


@api_bp.route("/admin/providers/<profile_code>", methods=["PATCH"])
@login_required(role="admin")
@csrf_protect
def admin_update_provider(profile_code):
    provider, error = _admin_provider(profile_code)
    if error:
        return error
    payload = _payload()
    for field in {
        "first_name", "last_name", "phone", "whatsapp", "city", "state",
        "latitude", "longitude", "hourly_rate", "experience_years",
        "availability", "profile_photo_url",
    }:
        if field in payload:
            setattr(provider, field, payload[field] or None)
    if "verified" in payload:
        provider.verified = str(payload["verified"]).lower() in {"1", "true", "yes"}
    db.session.commit()
    return jsonify(provider.to_admin_dto())


@api_bp.route("/admin/providers/<profile_code>/block", methods=["POST"])
@login_required(role="admin")
@csrf_protect
def admin_block_provider(profile_code):
    provider, error = _admin_provider(profile_code)
    if error:
        return error
    provider.is_active = False
    provider.blocked_at = datetime.now(timezone.utc)
    provider.blocked_reason = (_payload().get("reason") or "Blocked by admin").strip()
    db.session.commit()
    return jsonify(provider.to_admin_dto())


@api_bp.route("/admin/providers/<profile_code>/unblock", methods=["POST"])
@login_required(role="admin")
@csrf_protect
def admin_unblock_provider(profile_code):
    provider, error = _admin_provider(profile_code)
    if error:
        return error
    provider.is_active = True
    provider.blocked_at = None
    provider.blocked_reason = None
    db.session.commit()
    return jsonify(provider.to_admin_dto())


@api_bp.route("/admin/providers/<profile_code>/services", methods=["POST"])
@login_required(role="admin")
@csrf_protect
def admin_add_provider_service(profile_code):
    provider, error = _admin_provider(profile_code)
    if error:
        return error
    payload = _payload()
    service = Service.query.filter_by(slug=(payload.get("service_slug") or "").strip()).first()
    if not service:
        return jsonify({"error": "Service not found"}), 404
    relation = ProviderService.query.filter_by(provider_id=provider.id, service_id=service.id).first()
    if relation:
        return jsonify(relation.to_admin_dto(provider, service)), 200
    relation = ProviderService(provider_id=provider.id, service_id=service.id)
    relation.set_sub_services(payload.get("sub_services") or [])
    db.session.add(relation)
    db.session.commit()
    return jsonify(relation.to_admin_dto(provider, service)), 201


@api_bp.route("/admin/providers/<profile_code>/services/<service_slug>", methods=["PATCH"])
@login_required(role="admin")
@csrf_protect
def admin_update_provider_service(profile_code, service_slug):
    provider, error = _admin_provider(profile_code)
    if error:
        return error
    service = Service.query.filter_by(slug=service_slug).first()
    relation = ProviderService.query.filter_by(
        provider_id=provider.id, service_id=service.id if service else None
    ).first()
    if not relation or not service:
        return jsonify({"error": "Provider service relationship not found"}), 404
    payload = _payload()
    if "is_active" in payload:
        relation.is_active = str(payload["is_active"]).lower() in {"1", "true", "yes"}
        relation.blocked_at = None if relation.is_active else datetime.now(timezone.utc)
    if "blocked_reason" in payload:
        relation.blocked_reason = payload["blocked_reason"] or None
    if "sub_services" in payload:
        relation.set_sub_services(payload["sub_services"])
    db.session.commit()
    return jsonify(relation.to_admin_dto(provider, service))


@api_bp.route("/admin/services", methods=["POST"])
@login_required(role="admin")
@csrf_protect
def admin_create_service():
    payload = _payload()
    name = (payload.get("name") or "").strip()
    slug = (payload.get("slug") or "").strip()
    if not name or not slug:
        return jsonify({"error": "name and slug are required"}), 400
    if Service.query.filter_by(slug=slug).first():
        return jsonify({"error": "Service already exists"}), 409
    service = Service(
        name=name,
        slug=slug,
        display_order=payload.get("display_order") or 0,
        display_group=payload.get("display_group"),
        icon_key=payload.get("icon_key"),
        is_active=True,
    )
    db.session.add(service)
    db.session.commit()
    return jsonify(service.to_admin_dto()), 201


@api_bp.route("/admin/services/<service_slug>", methods=["PATCH"])
@login_required(role="admin")
@csrf_protect
def admin_update_service(service_slug):
    service = Service.query.filter_by(slug=service_slug).first()
    if not service:
        return jsonify({"error": "Service not found"}), 404
    payload = _payload()
    for field in {"name", "display_order", "display_group", "icon_key"}:
        if field in payload:
            setattr(service, field, payload[field])
    if "is_active" in payload:
        service.is_active = str(payload["is_active"]).lower() in {"1", "true", "yes"}
    db.session.commit()
    return jsonify(service.to_admin_dto())
