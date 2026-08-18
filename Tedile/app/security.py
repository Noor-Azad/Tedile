import hmac
import secrets
from functools import wraps

from flask import abort, session


_CSRF_SESSION_KEY = "csrf_token"


def get_csrf_token() -> str:
    token = session.get(_CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[_CSRF_SESSION_KEY] = token
    return token


def validate_csrf_token(token: str) -> bool:
    expected = session.get(_CSRF_SESSION_KEY)
    return bool(token and expected and hmac.compare_digest(token, expected))


def csrf_protect(view_fn):
    """Reject state-changing requests without the server-issued session token."""
    @wraps(view_fn)
    def wrapped(*args, **kwargs):
        from flask import request

        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return view_fn(*args, **kwargs)
        token = request.form.get("csrf_token") or request.headers.get("X-CSRFToken")
        if not validate_csrf_token(token):
            abort(400, description="Missing or invalid CSRF token.")
        return view_fn(*args, **kwargs)

    return wrapped
