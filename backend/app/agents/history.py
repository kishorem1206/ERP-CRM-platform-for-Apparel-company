"""Redis-backed conversation history for ERP agent sessions."""
import json
import redis.asyncio as aioredis

from app.core.config import settings

HISTORY_TTL = 86400   # 24 hours
MAX_MESSAGES = 40     # keep last 20 exchanges (user + assistant pairs)


def _key(conversation_id: str) -> str:
    return f"erp:chat:{conversation_id}"


async def load_history(conversation_id: str) -> list[dict]:
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        raw = await r.get(_key(conversation_id))
        return json.loads(raw) if raw else []
    finally:
        await r.aclose()


async def save_history(conversation_id: str, history: list[dict]) -> None:
    trimmed = history[-MAX_MESSAGES:]
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await r.setex(_key(conversation_id), HISTORY_TTL, json.dumps(trimmed))
    finally:
        await r.aclose()
