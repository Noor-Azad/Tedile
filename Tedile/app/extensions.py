try:
    from flask_sqlalchemy import SQLAlchemy
except ModuleNotFoundError:
    class _FallbackSession:
        def add(self, *args, **kwargs):
            return None

        def commit(self):
            return None

        def rollback(self):
            return None

    class SQLAlchemy:
        Model = object
        Integer = int
        String = str
        DateTime = object
        session = _FallbackSession()

        def __init__(self, *args, **kwargs):
            pass

        def init_app(self, app):
            return None

        def create_all(self):
            return None

        @staticmethod
        def Column(*args, **kwargs):
            return None

    db = SQLAlchemy()
else:
    db = SQLAlchemy()

try:
    from flask_migrate import Migrate
except ModuleNotFoundError:
    class Migrate:
        def init_app(self, app, db, **kwargs):
            return None

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# compare_type lets autogenerate detect column type changes, not just add/drop.
migrate = Migrate(compare_type=True)
limiter = Limiter(key_func=get_remote_address)
