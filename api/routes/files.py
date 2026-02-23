# api/routes/files.py
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
import structlog

from api.middleware.auth import get_current_user
from api.services.storage import r2_client

logger = structlog.get_logger()
router = APIRouter()

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Upload a file to R2 storage. Returns the file key and a presigned URL."""
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Allowed: {ALLOWED_CONTENT_TYPES}",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )

    tenant_id = current_user["tenant_id"]
    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "pdf"
    key = f"{tenant_id}/{uuid.uuid4()}.{ext}"

    try:
        r2_client.upload(file_bytes, key, content_type=file.content_type or "application/pdf")
    except Exception as e:
        logger.error("file_upload_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to upload file to storage",
        )

    presigned_url = r2_client.get_presigned_url(key)

    return {
        "file_key": key,
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": len(file_bytes),
        "presigned_url": presigned_url,
    }


def _assert_tenant_owns_file(file_key: str, tenant_id: str) -> None:
    """Verify the file key belongs to the requesting tenant."""
    if not file_key.startswith(f"{tenant_id}/"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )


@router.get("/{file_key:path}")
async def get_file_url(
    file_key: str,
    current_user: dict = Depends(get_current_user),
):
    """Get a presigned download URL for an existing file."""
    _assert_tenant_owns_file(file_key, current_user["tenant_id"])
    try:
        presigned_url = r2_client.get_presigned_url(file_key)
    except Exception as e:
        logger.error("presigned_url_failed", key=file_key, error=str(e))
        raise HTTPException(status_code=404, detail="File not found")

    return {"file_key": file_key, "presigned_url": presigned_url}


@router.delete("/{file_key:path}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_key: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a file from R2 storage."""
    _assert_tenant_owns_file(file_key, current_user["tenant_id"])
    try:
        r2_client.delete(file_key)
    except Exception as e:
        logger.error("file_delete_failed", key=file_key, error=str(e))
        raise HTTPException(status_code=404, detail="File not found or already deleted")
