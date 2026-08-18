"""Provision an admin account from a secure interactive terminal prompt.

Usage:
    flask db upgrade
    python -m database.create_admin

This command never prints a password or password hash. It does not alter an
existing account when the requested email already exists.
"""
import getpass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=False)

from app import create_app
from app.extensions import db
from app.models.user import User


def provision_admin(email: str, name: str, password: str, confirmation: str):
    email = (email or "").strip().lower()
    name = (name or "").strip()

    if not email or not name or not password:
        raise ValueError("email, name, and password are required")
    if password != confirmation:
        raise ValueError("password confirmation does not match")

    existing = User.query.filter_by(email=email).first()
    if existing:
        return {
            "created": False,
            "existing": True,
            "email": existing.email,
            "role": existing.role,
        }

    admin = User(email=email, name=name, role="admin")
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    return {
        "created": True,
        "existing": False,
        "email": admin.email,
        "role": admin.role,
    }


def main():
    email = input("Admin email: ").strip()
    name = input("Admin name: ").strip()
    password = getpass.getpass("Admin password: ")
    confirmation = getpass.getpass("Confirm admin password: ")

    app = create_app()
    with app.app_context():
        try:
            result = provision_admin(email, name, password, confirmation)
        except ValueError as exc:
            print(f"Provisioning failed: {exc}")
            raise SystemExit(1)

    if result["created"]:
        print(f"Admin account created: {result['email']}")
    else:
        print(
            f"Account already exists: {result['email']} "
            f"(role={result['role']}). No changes were made."
        )


if __name__ == "__main__":
    main()
