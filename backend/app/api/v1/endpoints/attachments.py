import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from sqlalchemy import select

from app.api.v1.deps import AuthUser, DBSession
from app.models.master import FileAttachment
from app.schemas.base import ApiResponse
from app.services.storage import delete_file, get_presigned_url, upload_file

router = APIRouter()

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
ALLOWED_MIME_PREFIXES = ("image/", "application/pdf", "application/vnd.", "text/csv", "text/plain")


@router.post("/attachments/upload")
async def upload(
    user: AuthUser,
    db: DBSession,
    file: UploadFile = File(...),
    entity_type: str = Form(...),
    entity_id: str = Form(...),
):
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 20 MB limit.")

    mime = file.content_type or ""
    if not any(mime.startswith(p) for p in ALLOWED_MIME_PREFIXES):
        raise HTTPException(status_code=415, detail=f"File type '{mime}' not allowed.")

    file_url, mime_type, size = upload_file(
        data=data,
        original_filename=file.filename or "upload",
        entity_type=entity_type,
        company_id=str(user.company_id),
    )

    record = FileAttachment(
        company_id=user.company_id,
        entity_type=entity_type,
        entity_id=uuid.UUID(entity_id),
        file_name=file.filename or "upload",
        file_url=file_url,
        file_size=size,
        mime_type=mime_type,
        uploaded_at=datetime.now(timezone.utc),
        uploaded_by=user.user_id,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return ApiResponse(success=True, data={
        "attachment_id": str(record.id),
        "file_url": file_url,
        "file_name": record.file_name,
        "file_size": size,
        "mime_type": mime_type,
    })


@router.get("/attachments/{attachment_id}/url")
async def get_attachment_url(attachment_id: str, user: AuthUser, db: DBSession):
    result = await db.execute(
        select(FileAttachment).where(
            FileAttachment.id == attachment_id,
            FileAttachment.company_id == user.company_id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Attachment not found.")
    return ApiResponse(success=True, data={
        "url": get_presigned_url(record.file_url),
        "file_name": record.file_name,
    })


@router.get("/attachments")
async def list_attachments(
    entity_type: str,
    entity_id: str,
    user: AuthUser,
    db: DBSession,
):
    result = await db.execute(
        select(FileAttachment).where(
            FileAttachment.company_id == user.company_id,
            FileAttachment.entity_type == entity_type,
            FileAttachment.entity_id == entity_id,
        ).order_by(FileAttachment.uploaded_at.desc())
    )
    rows = result.scalars().all()
    return ApiResponse(success=True, data=[{
        "id": str(r.id),
        "file_name": r.file_name,
        "file_size": r.file_size,
        "mime_type": r.mime_type,
        "url": get_presigned_url(r.file_url),
        "uploaded_at": r.uploaded_at.isoformat() if r.uploaded_at else None,
    } for r in rows])


@router.delete("/attachments/{attachment_id}")
async def delete_attachment(attachment_id: str, user: AuthUser, db: DBSession):
    result = await db.execute(
        select(FileAttachment).where(
            FileAttachment.id == attachment_id,
            FileAttachment.company_id == user.company_id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Attachment not found.")
    delete_file(record.file_url)
    await db.delete(record)
    await db.commit()
    return ApiResponse(success=True, message="Attachment deleted.")
