"""
Pluggable file storage backend.

STORAGE_BACKEND=local  → saves files under STORAGE_LOCAL_PATH (mounted volume)
STORAGE_BACKEND=s3     → uploads to AWS_S3_BUCKET / AWS_REGION
"""
import io
import mimetypes
import os
import uuid
from pathlib import Path

from app.core.config import settings


def _s3_client():
    import boto3
    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


def upload_file(
    data: bytes,
    original_filename: str,
    entity_type: str,
    company_id: str,
) -> tuple[str, str, int]:
    """
    Upload bytes and return (file_url, mime_type, file_size).

    local  → /media/<company_id>/<entity_type>/<uuid><ext>
    s3     → s3://<bucket>/<company_id>/<entity_type>/<uuid><ext>
              public URL: https://<bucket>.s3.<region>.amazonaws.com/<key>
    """
    ext = Path(original_filename).suffix.lower()
    key = f"{company_id}/{entity_type}/{uuid.uuid4().hex}{ext}"
    mime_type = mimetypes.guess_type(original_filename)[0] or "application/octet-stream"
    size = len(data)

    if settings.STORAGE_BACKEND == "s3":
        client = _s3_client()
        client.upload_fileobj(
            io.BytesIO(data),
            settings.AWS_S3_BUCKET,
            key,
            ExtraArgs={"ContentType": mime_type},
        )
        url = f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
    else:
        local_path = Path(settings.STORAGE_LOCAL_PATH) / key
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(data)
        url = f"/media/{key}"

    return url, mime_type, size


def delete_file(file_url: str) -> None:
    if settings.STORAGE_BACKEND == "s3":
        # Extract S3 key from URL
        prefix = f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/"
        if file_url.startswith(prefix):
            key = file_url[len(prefix):]
            _s3_client().delete_object(Bucket=settings.AWS_S3_BUCKET, Key=key)
    else:
        local_path = Path(settings.STORAGE_LOCAL_PATH) / file_url.removeprefix("/media/")
        if local_path.exists():
            local_path.unlink()


def get_presigned_url(file_url: str, expiry: int = 3600) -> str:
    """Return a temporary URL. Local: returns the URL unchanged (served by nginx)."""
    if settings.STORAGE_BACKEND == "s3":
        prefix = f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/"
        if file_url.startswith(prefix):
            key = file_url[len(prefix):]
            return _s3_client().generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.AWS_S3_BUCKET, "Key": key},
                ExpiresIn=expiry,
            )
    return file_url
