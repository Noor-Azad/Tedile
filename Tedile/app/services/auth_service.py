from app.extensions import db
from app.models.user import User


def register_user(email: str, password: str, name: str, role: str = "customer", phone: str = ""):
    email = (email or "").strip().lower()
    if not email or not password or not name:
        raise ValueError("email, password, and name are required")

    if User.query.filter_by(email=email).first():
        raise ValueError("An account with this email already exists")

    user = User(email=email, name=name, role=role, phone=phone)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def authenticate_user(email: str, password: str):
    email = (email or "").strip().lower()
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return None
    return user
