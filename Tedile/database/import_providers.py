"""Import external provider-service records into Tedile.

This script is an import tool only. It reads a supplied JSON file, validates
its structure, and writes through the existing ORM models. It never exposes
source records to a client and never runs as part of app startup.

Usage:
    flask db upgrade
    python -m database.import_providers data/imports/providers/2026-08-18/providers.json

The importer intentionally ignores the source numeric `id`, extraction
coordinates/distance metadata, profile URL, bio, and working-hours fields
because the current Tedile schema has no approved source-metadata fields for
those values. Provider coordinates are retained only in the existing private
Provider location columns for server-side proximity calculations.
"""
from __future__ import annotations

import argparse
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from app import create_app
from app.extensions import db
from app.models.provider import Provider
from app.models.provider_service import ProviderService
from app.models.service import Service


# Source service slug -> Tedile service slug. Existing catalog entries are
# reused; only missing target slugs are created by ensure_service_catalog().
SERVICE_MAPPING = {
    "ac-repair": "ac-repair",
    "accounting-tax-services": "accounting-tax-services",
    "alluminium-and-glass-work": "alluminium-and-glass-work",
    "bike-mechanic": "bike-mechanic",
    "Car - driver": "driver",
    "car-bike-wash-at-door-step": "car-bike-wash-at-door-step",
    "carpenter": "carpenter",
    "cctv-installation-repair": "cctv-installation-repair",
    "cleaning-staff": "cleaning-staff",
    "daily-labour": "daily-labour",
    "electrician": "electrician",
    "event-management": "event-management",
    "fire-extinguisher-refilling": "fire-extinguisher-refilling",
    "Home-Tuition-Teacher": "home-tuition-teacher",
    "instant-car": "instant-car",
    "interior-designer": "interior-designer",
    "j-c-b-service": "j-c-b-service",
    "makeup-artist": "makeup-artist",
    "mason": "mason",
    "mobile-repairing": "mobile-repairing",
    "painter": "painter",
    "photography-videography": "photography-videography",
    "plumber": "plumber",
    "plumber-cum-electrician": "plumber-cum-electrician",
    "solar-panel-setup": "solar-panel-setup",
    "toto-auto": "toto-auto",
    "toto-service-centre": "toto-service-centre",
    "veterinary-doctor": "veterinary-doctor",
    "water-purifier-and-kitchen-chimney-service": "water-purifier-kitchen-chimney-service",
    "welder": "welder",
}

# Explicit target labels for source categories that do not already exist in
# the Tedile seed catalog.
SERVICE_NAMES = {
    "alluminium-and-glass-work": "Alluminium and Glass Work",
    "car-bike-wash-at-door-step": "Car/Bike Wash at Door Step",
    "fire-extinguisher-refilling": "Fire Extinguisher Refilling",
    "instant-car": "Instant Car",
    "j-c-b-service": "J.C.B Service",
    "toto-auto": "Toto/Auto",
    "toto-service-centre": "Toto Service Centre",
    "driver": "Driver",
    "home-tuition-teacher": "Home Tuition Teacher",
    "ac-repair": "AC/Fridge Repair",
    "cleaning-staff": "Cleaning",
    "accounting-tax-services": "Accountant & GST/Tax Work",
    "water-purifier-kitchen-chimney-service": "Water Purifier & Kitchen Chimney Service",
}

REQUIRED_RECORD_KEYS = {"profile_code"}


def blank_to_none(value: Any):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def parse_decimal(value: Any):
    value = blank_to_none(value)
    if value is None:
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError):
        raise ValueError(f"invalid hourly_rate: {value!r}")


def parse_float(value: Any, field: str):
    value = blank_to_none(value)
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"invalid {field}: {value!r}")
    if field == "latitude" and not -90 <= result <= 90:
        raise ValueError(f"latitude out of range: {result}")
    if field == "longitude" and not -180 <= result <= 180:
        raise ValueError(f"longitude out of range: {result}")
    if field == "rating" and not 0 <= result <= 5:
        raise ValueError(f"rating out of range: {result}")
    return result


def parse_experience(value: Any):
    value = blank_to_none(value)
    if value is None:
        return 0
    match = re.match(r"^(\d+)", str(value))
    return int(match.group(1)) if match else 0


def parse_sub_services(value: Any):
    value = blank_to_none(value)
    if value is None:
        return []
    if isinstance(value, list):
        values = value
    else:
        values = re.split(r"[,|]", str(value))
    return sorted({str(item).strip() for item in values if str(item).strip()})


def parse_availability(value: Any):
    if isinstance(value, bool):
        return "available" if value else "offline"
    normalized = str(value or "").strip().lower()
    return "available" if normalized in {"true", "1", "yes", "available"} else "offline"


def normalize_records(payload: Any):
    if not isinstance(payload, dict):
        raise ValueError("JSON root must be an object")
    records = payload.get("providers")
    if not isinstance(records, list):
        raise ValueError("JSON must contain a providers list")
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"record {index} must be an object")
        missing = REQUIRED_RECORD_KEYS - record.keys()
        if missing:
            raise ValueError(f"record {index} missing required keys: {sorted(missing)}")
    return records


def service_source_slug(record):
    return blank_to_none(record.get("extracted_service_value")) or blank_to_none(record.get("service"))


def ensure_service_catalog(records, report):
    source_slugs = sorted({service_source_slug(record) for record in records if service_source_slug(record)})
    unknown = [slug for slug in source_slugs if slug not in SERVICE_MAPPING]
    if unknown:
        raise ValueError(f"No explicit Tedile service mapping for source slugs: {unknown}")

    target_slugs = {SERVICE_MAPPING[slug] for slug in source_slugs}
    services = {}
    for target_slug in sorted(target_slugs):
        service = Service.query.filter_by(slug=target_slug).first()
        if not service:
            source_name = next(
                (record.get("service_name") for record in records
                 if SERVICE_MAPPING.get(service_source_slug(record)) == target_slug),
                target_slug.replace("-", " ").title(),
            )
            service = Service(name=SERVICE_NAMES.get(target_slug, source_name), slug=target_slug)
            db.session.add(service)
            db.session.flush()
            report["services_created"] += 1
        services[target_slug] = service
        report["service_mappings"][target_slug] = sorted(
            {service_source_slug(record) for record in records
             if SERVICE_MAPPING.get(service_source_slug(record)) == target_slug}
        )
    return services


def validate_record(record, index):
    profile_code = blank_to_none(record.get("profile_code"))
    if not profile_code or len(str(profile_code)) > 64:
        raise ValueError(f"record {index}: profile_code is required and must be <= 64 characters")

    source_slug = service_source_slug(record)
    if not source_slug or source_slug not in SERVICE_MAPPING:
        raise ValueError(f"record {index}: unmapped or missing service slug {source_slug!r}")

    first_name = blank_to_none(record.get("first_name"))
    name = blank_to_none(record.get("name"))
    if not first_name and not name:
        raise ValueError(f"record {index}: provider name is required")

    return {
        "profile_code": str(profile_code),
        "source_slug": source_slug,
        "first_name": str(first_name or name).strip()[:120],
        "last_name": str(blank_to_none(record.get("last_name")) or "")[:120] or None,
        "phone": blank_to_none(record.get("phone")),
        "whatsapp": blank_to_none(record.get("whatsapp")),
        "city": blank_to_none(record.get("city")),
        "state": blank_to_none(record.get("state")),
        "latitude": parse_float(record.get("latitude"), "latitude"),
        "longitude": parse_float(record.get("longitude"), "longitude"),
        "hourly_rate": parse_decimal(record.get("hourly_rate")),
        "experience_years": parse_experience(record.get("experience")),
        "rating": parse_float(record.get("rating"), "rating") or 0.0,
        "availability": parse_availability(record.get("is_available")),
        "profile_photo_url": blank_to_none(record.get("profile_photo")),
        "sub_services": parse_sub_services(record.get("sub_services")),
    }


def import_paths(paths):
    paths = [Path(path) for path in paths]
    batches = []
    report = {
        "source_files": [],
        "total_records": 0,
        "unique_source_profile_codes": 0,
        "unique_providers_processed": 0,
        "providers_inserted": 0,
        "providers_updated": 0,
        "provider_services_inserted": 0,
        "duplicates_skipped": 0,
        "services_created": 0,
        "records_rejected": [],
        "service_mappings": {},
    }

    all_profile_codes = set()
    validated_records = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        records = normalize_records(payload)
        file_report = {
            "source": str(path),
            "total_records": len(records),
            "unique_source_profile_codes": len({record.get("profile_code") for record in records}),
            "provider_services_inserted": 0,
            "duplicates_skipped": 0,
            "records_rejected": [],
        }
        report["source_files"].append(file_report)
        report["total_records"] += len(records)
        all_profile_codes.update(record.get("profile_code") for record in records)
        batches.append(records)

        for index, record in enumerate(records):
            try:
                item = validate_record(record, index)
                validated_records.append((str(path), index, item, record))
            except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
                rejection = {"source": str(path), "record_index": index, "reason": str(exc)}
                file_report["records_rejected"].append(rejection)
                report["records_rejected"].append(rejection)

    report["unique_source_profile_codes"] = len(all_profile_codes)
    valid_source_records = [record for _, _, _, record in validated_records]
    unknown = sorted({
        service_source_slug(record)
        for record in valid_source_records
        if service_source_slug(record) not in SERVICE_MAPPING
    })
    if unknown:
        raise ValueError(f"No explicit Tedile service mapping for source slugs: {unknown}")

    inserted_profiles = set()
    updated_profiles = set()
    with db.session.begin():
        services = ensure_service_catalog(valid_source_records, report)

        for source, index, item, record in validated_records:
            try:
                target_slug = SERVICE_MAPPING[item["source_slug"]]
                service = services[target_slug]

                with db.session.begin_nested():
                    provider = Provider.query.filter_by(
                        profile_code=item["profile_code"]
                    ).one_or_none()
                    is_new_provider = provider is None
                    if is_new_provider:
                        provider = Provider(profile_code=item["profile_code"])
                        db.session.add(provider)

                    provider.first_name = item["first_name"]
                    provider.last_name = item["last_name"]
                    provider.phone = item["phone"]
                    provider.whatsapp = item["whatsapp"]
                    provider.city = item["city"]
                    provider.state = item["state"]
                    provider.latitude = item["latitude"]
                    provider.longitude = item["longitude"]
                    provider.hourly_rate = item["hourly_rate"]
                    provider.experience_years = item["experience_years"]
                    provider.rating = item["rating"]
                    provider.availability = item["availability"]
                    provider.profile_photo_url = item["profile_photo_url"]
                    if is_new_provider:
                        provider.verified = False
                    db.session.flush()

                    relation = ProviderService.query.filter_by(
                        provider_id=provider.id,
                        service_id=service.id,
                    ).one_or_none()
                    relation_created = relation is None
                    if relation_created:
                        relation = ProviderService(
                            provider_id=provider.id,
                            service_id=service.id,
                        )
                        db.session.add(relation)
                    merged = sorted(
                        set(relation.get_sub_services())
                        | set(item["sub_services"])
                    )
                    relation.set_sub_services(merged)

                # Only update counters after the savepoint committed.
                if is_new_provider:
                    inserted_profiles.add(item["profile_code"])
                else:
                    updated_profiles.add(item["profile_code"])
                if relation_created:
                    report["provider_services_inserted"] += 1
                    next(file_report for file_report in report["source_files"] if file_report["source"] == source)["provider_services_inserted"] += 1
                else:
                    report["duplicates_skipped"] += 1
                    next(file_report for file_report in report["source_files"] if file_report["source"] == source)["duplicates_skipped"] += 1
            except (KeyError, TypeError, ValueError, InvalidOperation, SQLAlchemyError) as exc:
                rejection = {"source": source, "record_index": index, "reason": str(exc)}
                report["records_rejected"].append(rejection)
                next(file_report for file_report in report["source_files"] if file_report["source"] == source)["records_rejected"].append(rejection)

    report["providers_inserted"] = len(inserted_profiles)
    report["providers_updated"] = len(updated_profiles - inserted_profiles)
    report["unique_providers_processed"] = len(
        inserted_profiles | updated_profiles
    )
    for file_report in report["source_files"]:
        file_report["providers_inserted"] = len({
            item["profile_code"]
            for source, _, item, _ in validated_records
            if source == file_report["source"] and item["profile_code"] in inserted_profiles
        })
        file_report["providers_updated"] = len({
            item["profile_code"]
            for source, _, item, _ in validated_records
            if source == file_report["source"] and item["profile_code"] in updated_profiles
        } - inserted_profiles)
    return report


def import_records(path: Path):
    """Backward-compatible single-file wrapper."""
    return import_paths([path])


def main():
    parser = argparse.ArgumentParser(description="Import external provider providers into Tedile")
    parser.add_argument("json_paths", type=Path, nargs="+")
    args = parser.parse_args()
    missing = [path for path in args.json_paths if not path.is_file()]
    if missing:
        parser.error(f"JSON file(s) not found: {missing}")

    app = create_app()
    with app.app_context():
        report = import_paths(args.json_paths)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
