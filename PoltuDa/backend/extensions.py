from collections import defaultdict, deque
from time import monotonic

from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
jwt = JWTManager()


class RateLimiter:
    """Simple in-memory rate limiter for API protection."""

    def __init__(self):
        self._requests = defaultdict(deque)

    def init_app(self, app):
        self.app = app
        return self

    def limit(self, rate_limit):
        def decorator(func):
            def wrapper(*args, **kwargs):
                from flask import jsonify, request

                if not self._allow_request(rate_limit, request.remote_addr or 'unknown'):
                    return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
                return func(*args, **kwargs)

            wrapper.__name__ = func.__name__
            return wrapper

        return decorator

    def _allow_request(self, rate_limit, client_key):
        try:
            max_requests, window_seconds = self._parse_rate_limit(rate_limit)
        except ValueError:
            return True

        now = monotonic()
        bucket = self._requests[(client_key, rate_limit)]
        bucket.append(now)

        cutoff = now - window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

        if len(bucket) > max_requests:
            return False
        return True

    @staticmethod
    def _parse_rate_limit(rate_limit):
        parts = rate_limit.split()
        if len(parts) != 3 or parts[1].lower() != 'per':
            raise ValueError('Unsupported rate limit format')

        max_requests = int(parts[0])
        period = parts[2].lower()
        mapping = {'second': 1, 'minute': 60, 'hour': 3600, 'day': 86400}
        if period not in mapping:
            raise ValueError('Unsupported rate limit period')

        return max_requests, mapping[period]


limiter = RateLimiter()
