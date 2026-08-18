import os
import re
from urllib.parse import quote

try:
    import boto3
except ImportError:  # pragma: no cover - handled gracefully in dev environments
    boto3 = None


def sanitize_filename(filename: str) -> str:
    if not filename:
        return "file"
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", filename.strip())
    safe = safe.strip("._")
    return safe or "file"


def build_s3_key(folder: str, record_id, original_filename: str) -> str:
    category = (folder or "documents").strip("/")
    record_slug = sanitize_filename(str(record_id))
    clean_name = sanitize_filename(original_filename)
    return f"{category}/{record_slug}/{clean_name}"


class StorageService:
    def __init__(self, bucket_name=None, region=None):
        self.bucket_name = bucket_name or os.getenv("S3_BUCKET_NAME", "tedile-app")
        self.region = region or os.getenv("AWS_REGION", "ap-south-1")

    def get_public_url(self, s3_key: str) -> str:
        key = s3_key.strip("/")
        return (
            f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{quote(key, safe='/')}"
        )

    def get_object_url(self, folder: str, record_id, filename: str) -> str:
        return self.get_public_url(build_s3_key(folder, record_id, filename))

    def upload_file(self, file_storage, folder: str, record_id, filename=None):
        file_name = filename or getattr(file_storage, "filename", None) or "upload.file"
        s3_key = build_s3_key(folder, record_id, file_name)

        if boto3 and os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
            client = boto3.client(
                "s3",
                region_name=self.region,
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            )
            file_storage.seek(0)
            client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_storage.read(),
                ContentType=getattr(file_storage, "content_type", None) or "application/octet-stream",
            )
            return self.get_public_url(s3_key), s3_key

        local_folder = os.path.join(os.getcwd(), "instance", "uploads", (folder or "documents").strip("/"), sanitize_filename(str(record_id)))
        os.makedirs(local_folder, exist_ok=True)
        target_path = os.path.join(local_folder, sanitize_filename(file_name))
        file_storage.seek(0)
        with open(target_path, "wb") as output_file:
            output_file.write(file_storage.read())

        local_url = f"/uploads/{(folder or 'documents').strip('/')}/{sanitize_filename(str(record_id))}/{sanitize_filename(file_name)}"
        return local_url, s3_key
