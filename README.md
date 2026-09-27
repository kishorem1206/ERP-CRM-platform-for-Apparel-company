# Apparel Manufacturing CRM/ERP

Enterprise ERP for apparel manufacturers — yarn to delivery, with AI agents.

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12 · FastAPI · SQLAlchemy 2.x · Alembic · Pydantic v2 |
| Database | PostgreSQL 16 |
| Cache / Queue | Redis 7 · Celery |
| AI Agents | gpt-oss:120b (OpenAI-compatible) · LangGraph |
| Frontend | Next.js 14 · TypeScript · Tailwind CSS · shadcn/ui · TanStack Query |
| Infrastructure | Docker · Docker Compose · NGINX |

## Project Structure

```
.
├── docs/               # Product document, architecture, API conventions
├── db/                 # Migrations (Alembic) + seed data
├── backend/            # FastAPI application
│   └── app/
│       ├── api/        # Route handlers
│       ├── core/       # Config, security, logging
│       ├── db/         # Session, base model
│       ├── models/     # SQLAlchemy ORM models
│       ├── schemas/    # Pydantic request/response schemas
│       ├── services/   # Business logic (pricing, inventory, tax)
│       ├── repositories/ # Data access layer
│       ├── domain/     # Business rules engine
│       ├── agents/     # LangGraph orchestrator + specialists
│       ├── workers/    # Celery background tasks
│       ├── middleware/ # Request ID, logging, auth
│       └── utils/      # Shared helpers
├── frontend/           # Next.js application
├── tests/              # Unit + integration tests
├── nginx/              # NGINX config
├── docker-compose.yml          # Development
├── docker-compose.prod.yml     # Production
└── .env.example        # Environment variable template
```

## Quick Start (Development)

### Prerequisites
- Docker + Docker Compose v2
- Node.js 20+ (for frontend local dev only)
- Python 3.12+ (for backend local dev only)

### 1. Clone and configure

```bash
git clone <repo>
cd apparel-erp
cp .env.example .env
# Edit .env — at minimum set:
#   POSTGRES_PASSWORD
#   APP_SECRET_KEY
#   JWT_SECRET_KEY
#   GPTOSS120B_API_KEY   (or LLM_API_KEY for other providers)
#   LLM_BASE_URL         (OpenAI-compat endpoint, e.g. https://open.bigmodel.cn/api/paas/v4/)
```

### 2. Start all services

```bash
docker compose up -d
```

This starts: PostgreSQL · Redis · Backend · Frontend · NGINX · Celery Worker

### 3. Run migrations

```bash
docker compose exec backend alembic upgrade head
```

### 4. Seed initial data

```bash
docker compose exec backend python -m app.db.seed
```

### 5. Access the application

| Service | URL |
|---------|-----|
| Frontend | http://localhost |
| Backend API | http://localhost/api/v1 |
| API Docs | http://localhost/api/v1/docs |
| Health | http://localhost/api/v1/health |

Default login: `admin@company.com` / `Admin@1234` (change immediately)

---

## Backend Local Development

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Run tests:
```bash
pytest tests/ -v
```

---

## Frontend Local Development

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
```

---

## Restart & Cache Clear

### Full restart (both frontend + backend)

```bash
cd "CRM platform"

# Stop everything
docker compose down

# Clear caches
rm -rf frontend/.next                                              # Next.js build cache
find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true  # Python bytecode

# Start fresh (rebuilds backend image)
docker compose up --build
```

> Use `docker compose up` (no `--build`) if you only changed frontend files and want a faster start.

### Frontend-only restart (local npm dev server)

```bash
# Stop dev server (Ctrl+C), then:
rm -rf frontend/.next
cd frontend && npm run dev
```

### Useful dev commands

| Goal | Command |
|---|---|
| Stop all services | `docker compose down` |
| Start with image rebuild | `docker compose up --build` |
| Start without rebuild | `docker compose up` |
| Restart one service | `docker compose restart backend` |
| Clear Next.js cache | `rm -rf frontend/.next` |
| Tail backend logs | `docker compose logs -f backend` |
| Tail frontend logs | `docker compose logs -f frontend` |
| Open a backend shell | `docker compose exec backend bash` |

---

## Database Migrations

```bash
# Create a new migration
docker compose exec backend alembic revision --autogenerate -m "describe change"

# Apply migrations
docker compose exec backend alembic upgrade head

# Rollback one step
docker compose exec backend alembic downgrade -1
```

---

## Environment Variables

See [.env.example](.env.example) for all available variables with descriptions.

Critical variables:
- `POSTGRES_PASSWORD` — database password
- `APP_SECRET_KEY` — application secret (64+ chars, random)
- `JWT_SECRET_KEY` — JWT signing key (64+ chars, random)
- `GPTOSS120B_API_KEY` — API key for gpt-oss:120b (required for AI agent features)
- `LLM_BASE_URL` — OpenAI-compatible base URL for the LLM provider
- `LLM_MODEL` — model name (default: `gpt-oss:120b`)
- `LLM_MAX_TOKENS` — max tokens per agent response (default: `20000`)

---

## Production Deployment

```bash
# Build and start production services
docker compose -f docker-compose.prod.yml up -d --build

# Run migrations
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

See [docs/deployment/](docs/deployment/) for NGINX SSL, backup, and rollback procedures.

---

## Architecture

See [docs/PRODUCT.md](docs/PRODUCT.md) for the full product document covering:
- Module map and bounded contexts
- Database schema and inventory ledger design
- API conventions
- LangGraph agent architecture
- Business rules engine
- GST/Tax engine
- Pricing engine
- Testing strategy

---

## Security

- Never commit `.env` files
- All secrets via environment variables only
- JWT access tokens expire in **8 hours**
- Refresh tokens are httpOnly cookies (30-day, SHA-256 hash stored in DB, rotated on use)
- In development (`is_development=true`), the refresh cookie uses `secure=False` + `samesite=lax` so it works over plain HTTP. In production it is `secure=True` + `samesite=lax`.
- All permissions are enforced server-side via RBAC (`user.require("permission.code")`)
- AI agents cannot bypass business rules or permissions
- Rate limiting on all public endpoints (login: 10/min, forgot-password: 5/5min)
