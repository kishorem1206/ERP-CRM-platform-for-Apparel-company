from fastapi import APIRouter

from app.api.v1.endpoints import cron, documents, admin, attachments, auth, health, agents, crm, notifications, products, master, purchase, sales, production, finance, inventory, reports, materials, whatsapp

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
# Also under /api/v1 so a host that only exposes the web server (which proxies
# /api/*) can health-check the API through it — Render does.
api_router.include_router(health.router, prefix="/api/v1", tags=["health"])
api_router.include_router(auth.router, prefix="/api/v1", tags=["auth"])
api_router.include_router(agents.router, prefix="/api/v1", tags=["agents"])
api_router.include_router(attachments.router, prefix="/api/v1", tags=["attachments"])
api_router.include_router(products.router, prefix="/api/v1", tags=["products"])
api_router.include_router(master.router, prefix="/api/v1", tags=["master"])
api_router.include_router(purchase.router, prefix="/api/v1", tags=["purchase"])
api_router.include_router(sales.router, prefix="/api/v1", tags=["sales"])
api_router.include_router(production.router, prefix="/api/v1", tags=["production"])
api_router.include_router(finance.router, prefix="/api/v1", tags=["finance"])
api_router.include_router(inventory.router, prefix="/api/v1", tags=["inventory"])
api_router.include_router(reports.router, prefix="/api/v1", tags=["reports"])
api_router.include_router(admin.router, prefix="/api/v1", tags=["admin"])
api_router.include_router(materials.router, prefix="/api/v1", tags=["materials"])
api_router.include_router(crm.router, prefix="/api/v1", tags=["crm"])
api_router.include_router(notifications.router, prefix="/api/v1", tags=["notifications"])
api_router.include_router(whatsapp.router, prefix="/api/v1", tags=["whatsapp"])
api_router.include_router(documents.router, prefix="/api/v1", tags=["documents"])
api_router.include_router(cron.router, prefix="/api/v1", tags=["internal"])
