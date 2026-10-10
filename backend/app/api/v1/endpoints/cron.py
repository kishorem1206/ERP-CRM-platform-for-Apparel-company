"""Scheduled-job trigger (replaces Celery beat).

An external scheduler — a Cloudflare Worker Cron Trigger in production, the
`cron` service in docker-compose locally — POSTs to /internal/cron/tick on a
fixed interval with the shared secret. Each tick runs whichever jobs in
app.workers.jobs.SCHEDULE are due, records the outcome in scheduled_job_runs,
and returns a summary. Not part of the user-facing API: it's secret-gated,
not permission-gated, and returns 404 when CRON_SECRET isn't configured.
"""
import hmac
import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine
from app.workers.jobs import SCHEDULE

router = APIRouter(prefix="/internal/cron", tags=["internal"])
log = logging.getLogger(__name__)

# Arbitrary constant identifying "the cron tick" for pg_try_advisory_lock.
_TICK_LOCK_ID = 640_064
# A job is due slightly before its full interval has elapsed, so jitter in
# the external trigger doesn't push it back a whole extra tick.
_DUE_SLACK_SECONDS = 60


def _check_secret(x_cron_secret: str | None) -> None:
    if not settings.CRON_SECRET:
        raise HTTPException(404, "Not Found")
    if not hmac.compare_digest(x_cron_secret or "", settings.CRON_SECRET):
        raise HTTPException(403, "Invalid cron secret")


async def _record(conn, job: str, **fields) -> None:
    cols = ", ".join(fields)
    vals = ", ".join(f":{k}" for k in fields)
    updates = ", ".join(f"{k} = EXCLUDED.{k}" for k in fields)
    await conn.execute(
        text(f"INSERT INTO scheduled_job_runs (job_name, {cols}) VALUES (:job, {vals}) "
             f"ON CONFLICT (job_name) DO UPDATE SET {updates}"),
        {"job": job, **fields},
    )
    await conn.commit()


@router.post("/tick")
async def cron_tick(x_cron_secret: str | None = Header(default=None), job: str | None = None):
    """Run every due job, or only `job` (regardless of schedule) when given."""
    _check_secret(x_cron_secret)
    if job is not None and job not in SCHEDULE:
        raise HTTPException(404, f"Unknown job: {job}")

    async with engine.connect() as conn:
        # Session-level advisory lock on this one connection: an overlapping
        # tick (slow run, duplicate trigger) skips instead of double-running.
        got_lock = (await conn.execute(text("SELECT pg_try_advisory_lock(:id)"), {"id": _TICK_LOCK_ID})).scalar()
        await conn.commit()
        if not got_lock:
            return {"success": True, "skipped": "another tick is already running", "ran": []}
        try:
            last_started = {
                name: started for name, started in
                (await conn.execute(text("SELECT job_name, last_started_at FROM scheduled_job_runs"))).all()
            }
            await conn.commit()
            now = datetime.now(timezone.utc)
            ran = []
            for name, (interval, fn) in SCHEDULE.items():
                if job is not None and name != job:
                    continue
                prev = last_started.get(name)
                if job is None and prev is not None and (now - prev).total_seconds() < interval - _DUE_SLACK_SECONDS:
                    continue
                started = time.monotonic()
                await _record(conn, name, last_started_at=datetime.now(timezone.utc), last_status="running")
                status, error, result = "ok", None, None
                try:
                    result = await fn()
                except Exception as exc:  # one failing job must not stop the others
                    status, error = "error", f"{type(exc).__name__}: {exc}"[:2000]
                    log.exception("Scheduled job %s failed", name)
                duration_ms = int((time.monotonic() - started) * 1000)
                await _record(conn, name, last_finished_at=datetime.now(timezone.utc), last_status=status,
                              last_error=error, last_duration_ms=duration_ms)
                ran.append({"job": name, "status": status, "duration_ms": duration_ms, "error": error,
                            "result": result if isinstance(result, (int, str)) else None})
            return {"success": True, "ran": ran}
        finally:
            await conn.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": _TICK_LOCK_ID})
            await conn.commit()


@router.get("/status")
async def cron_status(x_cron_secret: str | None = Header(default=None)):
    """Last run of every scheduled job — for checking the trigger is firing."""
    _check_secret(x_cron_secret)
    async with engine.connect() as conn:
        rows = (await conn.execute(text(
            "SELECT job_name, last_started_at, last_finished_at, last_status, last_error, last_duration_ms "
            "FROM scheduled_job_runs ORDER BY job_name"
        ))).mappings().all()
    known = {r["job_name"]: dict(r) for r in rows}
    return {
        "success": True,
        "jobs": [{**known.get(name, {"job_name": name, "last_status": "never_run"}), "interval_seconds": interval}
                 for name, (interval, _) in SCHEDULE.items()],
    }
