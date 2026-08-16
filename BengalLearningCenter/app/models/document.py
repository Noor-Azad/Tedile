from datetime import datetime

from app.extensions import db


if db is not None and hasattr(db, "Model") and callable(getattr(db, "Column", None)):
    class DocumentUpload(db.Model):
        __tablename__ = "document_uploads"

        id = db.Column(db.Integer, primary_key=True)
        owner_id = db.Column(db.String(255), nullable=False)
        category = db.Column(db.String(120), nullable=False)
        file_name = db.Column(db.String(255), nullable=False)
        s3_key = db.Column(db.String(500), nullable=False)
        file_url = db.Column(db.String(500), nullable=False)
        mime_type = db.Column(db.String(100), default="application/octet-stream")
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
else:
    class DocumentUpload:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
