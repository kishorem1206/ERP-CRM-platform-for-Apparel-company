# Single-container image for Render's free web service: the Next.js frontend
# and the FastAPI backend run side by side. Next.js listens on $PORT (the only
# port Render exposes) and proxies /api/* to uvicorn on 127.0.0.1:8000 through
# the rewrite already in frontend/next.config.mjs — so the browser talks to one
# origin (no CORS) and the workspace spends one set of free instance hours.
#
# Build context is the repository root:
#   docker build -f deploy/render/Dockerfile -t apparel-erp .

# ── Frontend build ────────────────────────────────────────────────────────────
FROM node:20-bookworm-slim AS web-deps
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

FROM node:20-bookworm-slim AS web-build
WORKDIR /web
COPY --from=web-deps /web/node_modules ./node_modules
COPY frontend/ .
# Rewrites are baked into the build, so the in-container backend address is
# fixed here rather than read at runtime.
ENV NEXT_TELEMETRY_DISABLED=1 \
    BACKEND_URL=http://127.0.0.1:8000
RUN mkdir -p public && npm run build

# ── Python dependencies ───────────────────────────────────────────────────────
# Built in a venv with a C toolchain (some pinned packages, e.g. orjson, have
# no prebuilt wheel on every platform), then copied into the slim runtime so
# the compiler doesn't ship.
FROM python:3.13-slim-bookworm AS py-deps
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev libffi-dev curl \
    && rm -rf /var/lib/apt/lists/*
# orjson etc. build with Rust when no wheel exists for this platform.
RUN curl -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
ENV PATH="/root/.cargo/bin:${PATH}"
RUN python -m venv /venv
ENV PATH="/venv/bin:${PATH}"
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# ── Runtime ───────────────────────────────────────────────────────────────────
FROM python:3.13-slim-bookworm

# Node runtime for the Next.js standalone server.
COPY --from=node:20-bookworm-slim /usr/local/bin/node /usr/local/bin/node

# libcairo/pango/gdk-pixbuf + fonts are for WeasyPrint PDF rendering.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libstdc++6 curl \
        libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
        libffi8 shared-mime-info fonts-liberation fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY --from=py-deps /venv /venv
ENV PATH="/venv/bin:${PATH}"

WORKDIR /app/backend
COPY backend/ .

COPY --from=web-build /web/.next/standalone /app/web
COPY --from=web-build /web/.next/static /app/web/.next/static
COPY --from=web-build /web/public /app/web/public

COPY deploy/render/start.sh /app/start.sh
RUN chmod +x /app/start.sh \
    && useradd -m -u 1000 appuser \
    && mkdir -p /media && chown -R appuser:appuser /app /media
USER appuser

ENV APP_ENV=production \
    NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000
EXPOSE 10000

CMD ["/app/start.sh"]
