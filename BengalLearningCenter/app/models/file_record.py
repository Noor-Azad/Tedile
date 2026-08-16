from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class FileRecord:
    id: str
    category: str
    owner_id: str
    original_name: str
    storage_key: str
    s3_url: str
    uploaded_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    mime_type: str = "application/octet-stream"
