from app.extensions import db
from app.models.user import User


def normalize_phone(phone):
    raw = (phone or "").strip()
    if not raw or any(ch not in "+0123456789 -()" for ch in raw):
        raise ValueError("Enter a valid mobile number")
    if "+" in raw:
        raise ValueError("Enter a valid mobile number")
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) != 10 or digits[0] not in "6789":
        raise ValueError("Enter a valid mobile number")
    return f"+91{digits}"


def validate_password(password):
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters")


def register_user(email: str, password: str, name: str, role: str = "customer", phone: str = ""):
    email = (email or "").strip().lower()
    if not email or not password or not name or not phone:
        raise ValueError("email, password, name, and mobile number are required")
    validate_password(password)
    phone = normalize_phone(phone)

    if User.query.filter_by(email=email).first():
        raise ValueError("An account with this email already exists")

    user = User(email=email, name=name, role=role, phone=phone)
    user.set_password(password)
    try:
        db.session.add(user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return user


def authenticate_user(email: str, password: str):
    email = (email or "").strip().lower()
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return None
    return user
