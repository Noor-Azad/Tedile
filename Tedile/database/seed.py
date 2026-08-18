"""Seed script for reference/demo data.

This inserts a realistic set of the 36 service categories and a couple of
example locations so the search API has something to query in a fresh
environment. It intentionally contains NO real provider data — provider
records must be created through signup/onboarding, not hardcoded here.

Requires migrations to be applied first: `flask db upgrade`.

Usage:
    python -m database.seed
"""
from sqlalchemy.exc import OperationalError, ProgrammingError

from app import create_app
from app.extensions import db
from app.models.location import Location
from app.models.service import Service

SERVICES = [
    ("Plumber", "plumber"),
    ("Electrician", "electrician"),
    ("Painter", "painter"),
    ("Carpenter", "carpenter"),
    ("Welder", "welder"),
    ("AC/Fridge Repair", "ac-repair"),
    ("Cleaning", "cleaning-staff"),
    ("Mason", "mason"),
    ("Home Tuition Teacher", "home-tuition-teacher"),
    ("CCTV Installation & Repair", "cctv-installation-repair"),
    ("Solar Panel Setup", "solar-panel-setup"),
    ("Interior Designer", "interior-designer"),
    ("Bike Mechanic", "bike-mechanic"),
    ("Car Mechanic", "car-mechanic"),
    ("Driver", "driver"),
    ("Event Management", "event-management"),
    ("Health Care", "health-care"),
    ("Photography & Videography", "photography-videography"),
    ("Veterinary Doctor", "veterinary-doctor"),
    ("Makeup Artist", "makeup-artist"),
    ("Accountant & GST/Tax Work", "accounting-tax-services"),
    ("Mobile Repairing", "mobile-repairing"),
    ("Water Purifier & Kitchen Chimney Service", "water-purifier-kitchen-chimney-service"),
    ("Daily Labour", "daily-labour"),
    ("Lawyer & Advocate", "lawyer-advocate"),
]

LOCATIONS = [
    ("Malda", "West Bengal", 25.0057449, 88.1398483),
    ("Kolkata", "West Bengal", 22.5726, 88.3639),
    ("Durgapur", "West Bengal", 23.5204, 87.3119),
    ("Siliguri", "West Bengal", 26.7271, 88.3953),
]


def seed():
    app = create_app()
    with app.app_context():
        try:
            for name, slug in SERVICES:
                if not Service.query.filter_by(slug=slug).first():
                    db.session.add(Service(name=name, slug=slug))

            for city, state, lat, lon in LOCATIONS:
                if not Location.query.filter_by(city=city).first():
                    db.session.add(Location(city=city, state=state, latitude=lat, longitude=lon))

            db.session.commit()
        except (OperationalError, ProgrammingError) as exc:
            db.session.rollback()
            raise RuntimeError(
                "Database tables not found. Run `flask db upgrade` before seeding."
            ) from exc

        print("Seed complete.")


if __name__ == "__main__":
    seed()
