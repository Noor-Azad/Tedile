from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from app.crypto import EncryptedString
from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)  # one-way hash only, never encrypted/decrypted
    role = db.Column(db.String(40), nullable=False, default="customer")  # customer | provider | admin
    name = db.Column(db.String(255), nullable=False)
    phone = db.Column(EncryptedString())  # encrypted at rest; private field
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def to_session_dict(self):
        """Minimal identity stored in the session cookie.

        Flask's default session is a signed-but-readable client-side cookie,
        so this must never include email, phone, or password_hash.
        """
        return {"id": self.id, "name": self.name, "role": self.role}

    def to_dict(self):
        """Full representation for server-side/internal use only.

        Never place this in a session cookie or return it from a public API
        response — it includes email and phone (decrypted).
        """
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "name": self.name,
            "phone": self.phone,
        }
