import os

try:
    import boto3
except ModuleNotFoundError:  # pragma: no cover
    boto3 = None


class S3Service:
    def __init__(self, bucket_name=None, region=None, access_key=None, secret_key=None):
        self.bucket_name = bucket_name or os.getenv("S3_BUCKET_NAME", "tedile-app")
        self.region = region or os.getenv("AWS_REGION", "ap-south-1")
        self.access_key = access_key or os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key = secret_key or os.getenv("AWS_SECRET_ACCESS_KEY")

    def is_configured(self):
        return bool(self.bucket_name and self.access_key and self.secret_key)

    def upload_file(self, file_obj, s3_key, content_type=None):
        if not self.is_configured() or boto3 is None:
            raise RuntimeError("AWS S3 is not configured. Add AWS credentials and bucket settings.")

        file_obj.seek(0)
        client = boto3.client(
            "s3",
            region_name=self.region,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )
        client.put_object(
            Bucket=self.bucket_name,
            Key=s3_key,
            Body=file_obj.read(),
            ContentType=content_type or "application/octet-stream",
        )

        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
