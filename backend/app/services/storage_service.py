"""Proctoring evidence storage on S3.

Objects are private. The database stores ``s3://bucket/key`` references and
API responses carry short-lived presigned URLs, so evidence is only viewable
by someone the API already authorised. Credentials come from the standard
boto3 chain (ECS task role / instance profile in AWS — no keys in config).
"""

import base64
import os
from typing import Any, Optional
import uuid

import boto3
from botocore.config import Config

from app.core.logging import logger

PRESIGN_SECONDS = int(os.getenv("EVIDENCE_URL_TTL_SECONDS", "900"))


class StorageService:
    def __init__(self):
        self.bucket = os.getenv("AWS_BUCKET_NAME", "")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.enabled = bool(self.bucket)
        self.s3_client = (
            boto3.client("s3", region_name=self.region, config=Config(signature_version="s3v4"))
            if self.enabled
            else None
        )

    def upload_base64_image(self, base64_str: str, prefix: str = "evidence") -> str:
        """Store a JPEG and return its ``s3://`` reference ("" when storage is disabled or fails)."""
        if not self.enabled:
            logger.warning("Evidence storage is not configured; recording the event without an image")
            return ""
        try:
            if "," in base64_str:  # data:image/jpeg;base64,...
                base64_str = base64_str.split(",", 1)[1]
            key = f"{prefix}/{uuid.uuid4().hex}.jpg"
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=base64.b64decode(base64_str),
                ContentType="image/jpeg",
                ServerSideEncryption="AES256",
            )
            return f"s3://{self.bucket}/{key}"
        except Exception as e:
            logger.error(f"Failed to upload image to S3: {str(e)}")
            return ""

    def is_own_reference(self, ref: Optional[str]) -> bool:
        return bool(self.enabled and ref and ref.startswith(f"s3://{self.bucket}/"))

    def presign(self, ref: Optional[str]) -> Optional[str]:
        """Turn a stored ``s3://`` reference into a temporary HTTPS URL."""
        if not ref:
            return None
        if not ref.startswith("s3://"):
            return ref  # legacy rows stored before references were introduced
        if not self.enabled:
            return None
        bucket, _, key = ref[len("s3://"):].partition("/")
        try:
            return self.s3_client.generate_presigned_url(
                "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=PRESIGN_SECONDS
            )
        except Exception as e:
            logger.error(f"Failed to presign evidence URL: {str(e)}")
            return None

    def presign_details(self, details: Optional[dict[str, Any]]) -> dict[str, Any]:
        details = dict(details or {})
        if details.get("image_url"):
            details["image_url"] = self.presign(details["image_url"])
        return details


storage_service = StorageService()
