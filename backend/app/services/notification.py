"""Notification creation and Redis pub/sub delivery."""
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


async def create_notification(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
    notification_type: str,
    title: str,
    body: str,
    user_id: uuid.UUID | None = None,
    data: dict | None = None,
) -> Notification:
    notif = Notification(
        company_id=company_id,
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        body=body,
        data=data,
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(notif)
    await db.flush()
    return notif


def publish_notification(company_id: str, payload: dict) -> None:
    """Sync Redis publish — called from Celery tasks."""
    import redis as sync_redis
    from app.core.config import settings
    r = sync_redis.from_url(settings.REDIS_URL)
    r.publish(f"erp:notif:{company_id}", json.dumps(payload))
    r.close()


async def list_notifications(
    db: AsyncSession,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    unread_only: bool = False,
    limit: int = 20,
) -> list[Notification]:
    q = (
        select(Notification)
        .where(
            Notification.company_id == company_id,
            (Notification.user_id == user_id) | (Notification.user_id.is_(None)),
        )
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    if unread_only:
        q = q.where(Notification.is_read.is_(False))
    result = await db.execute(q)
    return list(result.scalars().all())


async def count_unread(
    db: AsyncSession, company_id: uuid.UUID, user_id: uuid.UUID
) -> int:
    from sqlalchemy import func
    result = await db.execute(
        select(func.count()).where(
            Notification.company_id == company_id,
            (Notification.user_id == user_id) | (Notification.user_id.is_(None)),
            Notification.is_read.is_(False),
        )
    )
    return result.scalar_one() or 0


async def mark_read(db: AsyncSession, notif_id: uuid.UUID, company_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(Notification).where(
            Notification.id == notif_id, Notification.company_id == company_id
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        return False
    notif.is_read = True
    return True


async def mark_all_read(
    db: AsyncSession, company_id: uuid.UUID, user_id: uuid.UUID
) -> int:
    result = await db.execute(
        update(Notification)
        .where(
            Notification.company_id == company_id,
            (Notification.user_id == user_id) | (Notification.user_id.is_(None)),
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
        .returning(Notification.id)
    )
    return len(result.all())
