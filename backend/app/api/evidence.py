"""Serves proctoring evidence stored on the server's disk (EVIDENCE_DIR) through signed,
expiring links issued by app/services/storage_service.py. With S3 storage this route is unused:
S3 presigned URLs point straight at the bucket."""

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.services.storage_service import storage_service

router = APIRouter(prefix="/evidence", tags=["Evidence"])


@router.get("/{key:path}")
async def get_evidence(key: str, expires: int = Query(...), signature: str = Query(..., max_length=128)):
    path = storage_service.local_file(key, expires, signature)
    if path is None:
        # Same answer for unknown, expired and forged links.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    return FileResponse(
        path,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=300", "X-Content-Type-Options": "nosniff"},
    )
