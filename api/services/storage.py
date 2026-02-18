# api/services/storage.py
import boto3
from botocore.config import Config
from api.config import settings
import structlog

logger = structlog.get_logger()


class R2Client:
    def __init__(self):
        self.s3 = boto3.client(
            "s3",
            endpoint_url=settings.R2_ENDPOINT_URL,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
        self.bucket = settings.R2_BUCKET_NAME

    def upload(
        self, file_bytes: bytes, key: str, content_type: str = "application/pdf"
    ) -> str:
        self.s3.put_object(
            Bucket=self.bucket, Key=key, Body=file_bytes, ContentType=content_type
        )
        logger.info("r2_uploaded", key=key, size=len(file_bytes))
        return key

    def download(self, key: str) -> bytes:
        return self.s3.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    def delete(self, key: str):
        self.s3.delete_object(Bucket=self.bucket, Key=key)
        logger.info("r2_deleted", key=key)


r2_client = R2Client()
