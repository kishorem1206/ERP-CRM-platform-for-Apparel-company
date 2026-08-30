import json
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import select

from app.api.v1.deps import AuthUser, DBSession
from app.core.security import decode_token
from app.db.session import AsyncSessionLocal
from app.models.notification import Notification
from app.models.user import User
from app.schemas.base import ApiResponse
from app.services.notification import (
    count_unread, list_notifications, mark_all_read, mark_read
)

router = APIRouter()


def _out(n: Notification) -> dict:
    return {
        "id": str(n.id),
        "notification_type": n.notification_type,
        "title": n.title,
        "body": n.body,
        "data": n.data,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat(),
    }


@router.get("/notifications/count", response_model=ApiResponse)
async def get_unread_count(user: AuthUser, db: DBSession):
    count = await count_unread(db, user.company_id, user.user_id)
    return ApiResponse(success=True, data={"unread": count})


@router.get("/notifications", response_model=ApiResponse)
async def get_notifications(
    user: AuthUser, db: DBSession,
    unread_only: bool = False,
    limit: int = Query(default=20, le=50),
):
    items = await list_notifications(db, user.company_id, user.user_id, unread_only, limit)
    return ApiResponse(success=True, data=[_out(n) for n in items])


@router.post("/notifications/{notif_id}/read", response_model=ApiResponse)
async def read_one(notif_id: UUID, user: AuthUser, db: DBSession):
    ok = await mark_read(db, notif_id, user.company_id)
    return ApiResponse(success=ok, message="Marked as read" if ok else "Not found")


@router.post("/notifications/read-all", response_model=ApiResponse)
async def read_all(user: AuthUser, db: DBSession):
    count = await mark_all_read(db, user.company_id, user.user_id)
    return ApiResponse(success=True, data={"marked": count}, message=f"{count} notifications marked as read")


# ─── WebSocket ───────────────────────────────────────────────────────────────

@router.websocket("/ws/notifications")
async def ws_notifications(websocket: WebSocket, token: str = Query(...)):
    """Real-time notification delivery via Redis pub/sub."""
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001)
        return

    company_id = payload.get("company_id")
    if not company_id:
        await websocket.close(code=4001)
        return

    await websocket.accept()

    import redis.asyncio as aioredis
    from app.core.config import settings

    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe(f"erp:notif:{company_id}")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await pubsub.unsubscribe()
        await r.aclose()
