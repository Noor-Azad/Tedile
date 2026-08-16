import re
from datetime import datetime

from flask_jwt_extended import create_access_token

from backend.extensions import db
from backend.models import Provider, User


class AuthService:
    @staticmethod
    def _validate_email(email):
        if not re.fullmatch(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise ValueError('Invalid email format')
        return email

    @staticmethod
    def _validate_password(password):
        if len(password) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', password):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', password):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', password):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[^A-Za-z0-9]', password):
            raise ValueError('Password must contain at least one special character')
        return password

    @staticmethod
    def register(data):
        required = ['email', 'password', 'first_name', 'last_name', 'phone', 'user_type']
        missing = [field for field in required if not data.get(field)]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        email = AuthService._validate_email(str(data['email']).strip().lower())
        password = AuthService._validate_password(str(data['password']))
        user_type = str(data['user_type']).strip().lower()

        if user_type not in {'customer', 'provider', 'admin'}:
            raise ValueError('Invalid user_type. Must be "customer", "provider", or "admin"')

        if User.query.filter_by(email=email).first():
            raise ValueError('Email already registered')

        user = User(
            email=email,
            first_name=str(data['first_name']).strip(),
            last_name=str(data['last_name']).strip(),
            phone=str(data['phone']).strip(),
            user_type=user_type,
            city=(data.get('city') or '').strip() or None,
            district=(data.get('district') or '').strip() or None,
            area=(data.get('area') or '').strip() or None,
        )
        user.set_password(password)

        db.session.add(user)
        db.session.flush()

        if user_type == 'provider' and data.get('service_id') is not None:
            provider = Provider(
                user_id=user.id,
                service_id=int(data['service_id']),
                experience_years=int(data.get('experience_years') or 0),
            )
            db.session.add(provider)

        db.session.commit()
        return user

    @staticmethod
    def login(email, password):
        user = User.query.filter_by(email=str(email).strip().lower()).first()
        if not user or not user.check_password(password):
            raise ValueError('Invalid email or password')
        if not user.is_active:
            raise PermissionError('User account is inactive')

        token = create_access_token(identity=str(user.id))
        return {'access_token': token, 'user': user.to_dict()}

    @staticmethod
    def update_profile(user, data):
        allowed_fields = {
            'first_name': lambda v: str(v).strip(),
            'last_name': lambda v: str(v).strip(),
            'phone': lambda v: str(v).strip(),
            'bio': lambda v: str(v).strip(),
            'city': lambda v: (str(v).strip() or None),
            'district': lambda v: (str(v).strip() or None),
            'area': lambda v: (str(v).strip() or None),
            'latitude': lambda v: float(v),
            'longitude': lambda v: float(v),
        }

        for field, parser in allowed_fields.items():
            if field in data and data[field] is not None:
                setattr(user, field, parser(data[field]))

        user.updated_at = datetime.utcnow()
        db.session.commit()
        return user

    @staticmethod
    def change_password(user, old_password, new_password):
        if not old_password or not new_password:
            raise ValueError('Old password and new password are required')
        if not user.check_password(old_password):
            raise ValueError('Old password is incorrect')
        user.set_password(str(new_password))
        db.session.commit()
        return True
