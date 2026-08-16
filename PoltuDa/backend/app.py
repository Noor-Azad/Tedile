"""
PoltuDa.in - Local Service Provider Marketplace
Main Flask Application
"""
import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import get_config
from models import db

# Import blueprints
from routes_auth import auth_bp
from routes_services import services_bp
from routes_providers import providers_bp


def create_app():
    """Application factory"""
    app = Flask(__name__)
    
    # Load configuration
    config_class = get_config()
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": app.config['CORS_ORIGINS']}})
    jwt = JWTManager(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(services_bp)
    app.register_blueprint(providers_bp)
    
    # Create upload folder
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Error handlers
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
    
    # Health check route
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({'status': 'ok', 'message': 'PoltuDa.in API is running'}), 200

    @app.route('/', methods=['GET'])
    def frontend():
        return send_from_directory(os.path.dirname(app.root_path), 'index.html')

    @app.route('/manifest.json', methods=['GET'])
    def manifest():
        return send_from_directory(os.path.dirname(app.root_path), 'manifest.json')
    
    # Context processor
    with app.app_context():
        db.create_all()
    
    return app


# Create app instance
app = create_app()


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', '5000')),
        debug=False,
        use_reloader=False
    )
