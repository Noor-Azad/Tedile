"""
PoltuDa.in - Local Service Provider Marketplace
Main Flask Application
"""
import os
import socket
import sys

if __package__ is None or __package__ == '':
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_migrate import Migrate

if __package__ is None or __package__ == '':
    from backend.config import get_config
    from backend.extensions import db, jwt, limiter
    from backend.routes_auth import auth_bp
    from backend.routes_services import services_bp
    from backend.routes_providers import providers_bp
else:
    from .config import get_config
    from .extensions import db, jwt, limiter
    from .routes_auth import auth_bp
    from .routes_services import services_bp
    from .routes_providers import providers_bp


def create_app(config_object=None):
    """Application factory"""
    app = Flask(__name__)

    config_class = config_object or get_config()
    app.config.from_object(config_class)

    db.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)
    Migrate(app, db)
    CORS(app, resources={r"/api/*": {"origins": app.config['CORS_ORIGINS']}})

    app.register_blueprint(auth_bp)
    app.register_blueprint(services_bp)
    app.register_blueprint(providers_bp)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'; frame-ancestors 'none'"
        return response

    @app.before_request
    def enforce_https_in_production():
        if app.config.get('ENV') == 'production' and not request.is_secure:
            proto = request.headers.get('X-Forwarded-Proto', 'http')
            if proto != 'https':
                return jsonify({'error': 'HTTPS required'}), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({'error': 'Unauthorized'}), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({'error': 'Forbidden'}), 403

    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({'status': 'ok', 'message': 'PoltuDa.in API is running'}), 200

    @app.route('/', methods=['GET'])
    def frontend():
        return send_from_directory(os.path.dirname(app.root_path), 'index.html')

    @app.route('/manifest.json', methods=['GET'])
    def manifest():
        return send_from_directory(os.path.dirname(app.root_path), 'manifest.json')

    with app.app_context():
        db.create_all()

    return app


app = create_app()


def get_available_port(default_port=5000):
    preferred_port = int(os.getenv('PORT', str(default_port)))
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if sock.connect_ex(('127.0.0.1', preferred_port)) != 0:
            return preferred_port
    return preferred_port + 1 if preferred_port < 65535 else 5001


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=get_available_port(),
        debug=False,
        use_reloader=False
    )
