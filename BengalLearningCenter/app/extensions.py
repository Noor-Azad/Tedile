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
