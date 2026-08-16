"""
Authentication routes
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

try:
    from .extensions import db, limiter
    from .models import User
    from .services.auth_service import AuthService
except ImportError:  # pragma: no cover - fallback for script execution
    from extensions import db, limiter
    from models import User
    from services.auth_service import AuthService

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
@limiter.limit("5 per minute")
def register():
    """Register a new user"""
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid JSON payload'}), 400

    try:
        user = AuthService.register(data)
        return jsonify({'message': 'User registered successfully', 'user': user.to_dict()}), 201
    except ValueError as exc:
        code = 409 if 'already registered' in str(exc).lower() else 400
        return jsonify({'error': str(exc)}), code
    except Exception as exc:
        db.session.rollback()
        return jsonify({'error': 'Registration failed'}), 500


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    """Login user and return JWT token"""
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid JSON payload'}), 400

    email = (data.get('email') or '').strip()
    password = data.get('password')
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    try:
        result = AuthService.login(email, password)
        return jsonify({'message': 'Login successful', **result}), 200
    except (ValueError, PermissionError) as exc:
        status_code = 403 if 'inactive' in str(exc).lower() else 401
        return jsonify({'error': str(exc)}), status_code


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current authenticated user"""
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    user_data = user.to_dict()
    
    # Add provider info if provider
    if user.user_type == 'provider' and user.provider_profile:
        user_data['provider'] = user.provider_profile.to_dict()
    
    return jsonify(user_data), 200


@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update user profile"""
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid JSON payload'}), 400

    try:
        updated_user = AuthService.update_profile(user, data)
        return jsonify({'message': 'Profile updated successfully', 'user': updated_user.to_dict()}), 200
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Profile update failed'}), 500


@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user password"""
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid JSON payload'}), 400

    try:
        AuthService.change_password(user, data.get('old_password'), data.get('new_password'))
        return jsonify({'message': 'Password changed successfully'}), 200
    except ValueError as exc:
        status_code = 401 if 'incorrect' in str(exc).lower() else 400
        return jsonify({'error': str(exc)}), status_code
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Password change failed'}), 500
