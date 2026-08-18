"""Field-level encryption for PII stored at rest (e.g. phone numbers).

Only used for columns that are never queried by equality (no WHERE ... = ),
since ciphertext is non-deterministic. Do NOT use this for lookup columns
such as login email or slugs/codes used in WHERE clauses.
"""
import logging

try:
    from cryptography.fernet import Fernet, InvalidToken
except ModuleNotFoundError:  # pragma: no cover - dependency is in requirements.txt
    Fernet = None
    InvalidToken = Exception

from app.extensions import db

logger = logging.getLogger(__name__)


def _fernet():
    from flask import current_app

    key = current_app.config["ENCRYPTION_KEY"]
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


class EncryptedString(db.TypeDecorator):
    """Transparently encrypts a string column at rest using Fernet.

    Plaintext only ever exists in application memory; the database column
    stores ciphertext. Decryption happens automatically when the ORM
    attribute is read within an app/request context.

    There is no plaintext fallback: if the `cryptography` package is
    unavailable, instantiating this type raises immediately rather than
    silently storing values unencrypted.
    """

    impl = db.Text
    cache_ok = True

    def __init__(self, *args, **kwargs):
        if Fernet is None:
            raise RuntimeError(
                "The 'cryptography' package is required to use EncryptedString "
                "columns (install it via requirements.txt). Refusing to store "
                "PII unencrypted."
            )
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value, dialect):
        if not value:
            return value
        return _fernet().encrypt(value.encode()).decode()

    def process_result_value(self, value, dialect):
        if not value:
            return value
        try:
            return _fernet().decrypt(value.encode()).decode()
        except InvalidToken:
            # Predates encryption, or the key was rotated without re-encrypting.
            logger.warning("Unable to decrypt stored value; returning None")
            return None

            return None
