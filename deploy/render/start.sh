#!/bin/bash
# Container entrypoint for the Render image (deploy/render/Dockerfile).
# Brings the database up to date, then runs the API and the web server
# together. If either process exits, the container exits too, so Render
# restarts it instead of serving half an app.
set -euo pipefail

cd /app/backend

echo "[start] applying database migrations"
python -m alembic upgrade head

echo "[start] ensuring base permissions/master data (idempotent)"
python -m app.db.seed

echo "[start] starting API on 127.0.0.1:8000"
# One worker: the free instance has 512 MB. --proxy-headers so client IPs
# (used by login rate limiting) come from Render's X-Forwarded-For.
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 \
    --proxy-headers --forwarded-allow-ips='*' &
API_PID=$!

# Don't put the web server in front of an API that isn't listening yet.
for _ in $(seq 1 60); do
    curl -fs http://127.0.0.1:8000/health >/dev/null 2>&1 && break
    sleep 1
done

echo "[start] starting web on 0.0.0.0:${PORT}"
cd /app/web
HOSTNAME=0.0.0.0 node server.js &
WEB_PID=$!

trap 'kill -TERM "$API_PID" "$WEB_PID" 2>/dev/null; wait' TERM INT
set +e  # a non-zero exit from either process must reach the cleanup below
wait -n "$API_PID" "$WEB_PID"
EXIT_CODE=$?
echo "[start] a process exited (code ${EXIT_CODE}); shutting down so Render restarts the service"
kill -TERM "$API_PID" "$WEB_PID" 2>/dev/null || true
exit "$EXIT_CODE"
