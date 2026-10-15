"""Proctoring evidence storage: Amazon S3, or a directory on the server.

- S3 (``AWS_BUCKET_NAME``): private objects; the database stores ``s3://bucket/key``
  references and API responses carry short-lived presigned URLs. Credentials come from the
  standard boto3 chain (ECS task role / instance profile - no keys in config).
- Local disk (``EVIDENCE_DIR``, e.g. a campus server): files under that directory; the database
  stores ``local://key`` and API responses carry short-lived links to ``/api/evidence/<key>``
  signed with ``SECRET_KEY`` (HMAC), so - as with S3 - only someone the API already authorised
  gets a working link, and links expire.

Neither set: events are recorded without an image.
"""

import base64
import hashlib
import hmac
import os
import re
import time
from pathlib import Path
from typing import Any, Optional
import uuid

from app.core.logging import logger

PRESIGN_SECONDS = int(os.getenv("EVIDENCE_URL_TTL_SECONDS", "900"))
# Keys this service generates: evidence/<session id>/<32 hex>.jpg (nothing else is ever served).
_KEY = re.compile(r"^[a-z]+/[0-9a-fA-F-]{1,64}/[0-9a-f]{32}\.jpg$")


class StorageService:
    def __init__(self):
        self.bucket = os.getenv("AWS_BUCKET_NAME", "")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.local_dir = Path(os.getenv("EVIDENCE_DIR", "")) if os.getenv("EVIDENCE_DIR") else None
        self.mode = "s3" if self.bucket else ("local" if self.local_dir else None)
        self.enabled = self.mode is not None
        self.s3_client = None
        if self.mode == "s3":
            import boto3
            from botocore.config import Config

            self.s3_client = boto3.client("s3", region_name=self.region, config=Config(signature_version="s3v4"))

    # ---- writing -----------------------------------------------------------------------------

    def upload_base64_image(self, base64_str: str, prefix: str = "evidence") -> str:
        """Store a JPEG and return its reference ("" when storage is disabled or fails)."""
        if not self.enabled:
            logger.warning("Evidence storage is not configured; recording the event without an image")
            return ""
        try:
            if "," in base64_str:  # data:image/jpeg;base64,...
                base64_str = base64_str.split(",", 1)[1]
            data = base64.b64decode(base64_str)
            key = f"{prefix}/{uuid.uuid4().hex}.jpg"
            if self.mode == "local":
                path = self.local_dir / key
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                return f"local://{key}"
            self.s3_client.put_object(
                Bucket=self.bucket, Key=key, Body=data, ContentType="image/jpeg", ServerSideEncryption="AES256",
            )
            return f"s3://{self.bucket}/{key}"
        except Exception as e:
            logger.error("evidence.store_failed", error=str(e))
            return ""

    def is_own_reference(self, ref: Optional[str]) -> bool:
        if not (self.enabled and ref):
            return False
        if self.mode == "local":
            return ref.startswith("local://") and bool(_KEY.match(ref[len("local://"):]))
        return ref.startswith(f"s3://{self.bucket}/")

    # ---- reading -----------------------------------------------------------------------------

    def presign(self, ref: Optional[str]) -> Optional[str]:
        """Turn a stored reference into a temporary URL."""
        if not ref:
            return None
        if ref.startswith("local://"):
            return self._local_url(ref[len("local://"):]) if self.mode == "local" else None
        if not ref.startswith("s3://"):
            return ref  # legacy rows stored before references were introduced
        if self.mode != "s3":
            return None
        bucket, _, key = ref[len("s3://"):].partition("/")
        try:
            return self.s3_client.generate_presigned_url(
                "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=PRESIGN_SECONDS
            )
        except Exception as e:
            logger.error("evidence.presign_failed", error=str(e))
            return None

    def presign_details(self, details: Optional[dict[str, Any]]) -> dict[str, Any]:
        details = dict(details or {})
        if details.get("image_url"):
            details["image_url"] = self.presign(details["image_url"])
        return details

    # ---- local signed links -------------------------------------------------------------------

    @staticmethod
    def _signature(key: str, expires: int) -> str:
        from app.core.config import settings

        message = f"{key}:{expires}".encode()
        return hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()

    def _local_url(self, key: str) -> Optional[str]:
        if not _KEY.match(key):
            return None
        expires = int(time.time()) + PRESIGN_SECONDS
        base = os.getenv("PUBLIC_API_URL", "").rstrip("/")  # same-origin deployments may leave it empty
        return f"{base}/api/evidence/{key}?expires={expires}&signature={self._signature(key, expires)}"

    def local_file(self, key: str, expires: int, signature: str) -> Optional[Path]:
        """The file behind a signed link, or None if the link is invalid, expired or unknown."""
        if self.mode != "local" or not _KEY.match(key) or expires < time.time():
            return None
        if not hmac.compare_digest(self._signature(key, expires), signature or ""):
            return None
        path = (self.local_dir / key).resolve()
        if self.local_dir.resolve() not in path.parents or not path.is_file():
            return None
        return path


storage_service = StorageService()
