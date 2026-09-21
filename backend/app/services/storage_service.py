import os
import uuid
import base64
import boto3
from botocore.exceptions import ClientError
from app.core.logging import logger

class StorageService:
    def __init__(self):
        self.bucket = os.getenv("AWS_BUCKET_NAME", "")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.enabled = bool(self.bucket)
        if self.enabled:
            self.s3_client = boto3.client('s3', region_name=self.region)
        else:
            self.s3_client = None

    def upload_base64_image(self, base64_str: str, prefix: str = "evidence") -> str:
        """Uploads a base64 image to S3 and returns the public URL."""
        if not self.enabled:
            logger.info("[STORAGE MOCK] Image upload skipped (AWS_BUCKET_NAME not set)")
            return "https://mock-storage.local/evidence.jpg"

        try:
            # Strip header if present (e.g. data:image/jpeg;base64,...)
            if "," in base64_str:
                base64_str = base64_str.split(",")[1]
            
            image_data = base64.b64decode(base64_str)
            filename = f"{prefix}/{uuid.uuid4().hex}.jpg"
            
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=filename,
                Body=image_data,
                ContentType='image/jpeg'
                # Note: ACL='public-read' depends on bucket policies. 
                # Assuming presigned URLs are better for exam evidence security, 
                # but for simplicity we return the raw object URL if public, or just the key.
            )
            
            return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{filename}"
        except Exception as e:
            logger.error(f"Failed to upload image to S3: {str(e)}")
            return ""

storage_service = StorageService()
