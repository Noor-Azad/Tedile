from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt_identity

from backend.extensions import db
from backend.models import User


def role_required(*allowed_roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user_id = get_jwt_identity()
            user = db.session.get(User, user_id)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            if user.user_type not in allowed_roles:
                return jsonify({'error': 'Access denied: insufficient role'}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator
