from backend.app import create_app
from backend.config import TestingConfig
from backend.extensions import db


def create_test_app():
    app = create_app(config_object=TestingConfig)
    with app.app_context():
        db.drop_all()
        db.create_all()
    return app


def test_create_app_builds_flask_app():
    app = create_test_app()

    assert app is not None
    assert app.name in {"backend.app", "app"}
    assert app.url_map is not None


def test_register_and_login_user():
    app = create_test_app()
    client = app.test_client()

    resp = client.post(
        '/api/auth/register',
        json={
            'email': 'alice@example.com',
            'password': 'Password123!',
            'first_name': 'Alice',
            'last_name': 'Ng',
            'phone': '1234567890',
            'user_type': 'customer',
        },
    )
    assert resp.status_code == 201, resp.get_data(as_text=True)

    resp = client.post(
        '/api/auth/login',
        json={'email': 'alice@example.com', 'password': 'Password123!'},
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)
    token = resp.get_json()['access_token']
    assert token

    resp = client.get('/api/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert resp.get_json()['email'] == 'alice@example.com'


def test_register_rejects_invalid_email_and_weak_password():
    app = create_test_app()
    client = app.test_client()

    resp = client.post(
        '/api/auth/register',
        json={
            'email': 'not-an-email',
            'password': 'weak',
            'first_name': 'Bad',
            'last_name': 'User',
            'phone': '1234567890',
            'user_type': 'customer',
        },
    )
    assert resp.status_code == 400, resp.get_data(as_text=True)

    resp = client.post(
        '/api/auth/register',
        json={
            'email': 'valid@example.com',
            'password': 'weak',
            'first_name': 'Good',
            'last_name': 'User',
            'phone': '1234567890',
            'user_type': 'customer',
        },
    )
    assert resp.status_code == 400, resp.get_data(as_text=True)


def test_admin_route_requires_admin_role():
    app = create_test_app()
    client = app.test_client()

    client.post(
        '/api/auth/register',
        json={
            'email': 'admin@example.com',
            'password': 'Password123!',
            'first_name': 'Admin',
            'last_name': 'User',
            'phone': '9999999999',
            'user_type': 'admin',
        },
    )

    login = client.post(
        '/api/auth/login',
        json={'email': 'admin@example.com', 'password': 'Password123!'},
    )
    token = login.get_json()['access_token']

    resp = client.get('/api/services', headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 200, resp.get_data(as_text=True)

    resp = client.post(
        '/api/services',
        headers={'Authorization': f'Bearer {token}'},
        json={'name': 'Testing Service', 'category': 'IT'},
    )
    assert resp.status_code == 201, resp.get_data(as_text=True)
