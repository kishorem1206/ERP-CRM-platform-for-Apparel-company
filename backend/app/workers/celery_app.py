from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "apparel_erp",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "refresh-inventory-balance-every-5m": {
            "task": "app.workers.tasks.refresh_inventory_balance",
            "schedule": 5 * 60,
        },
        "expire-refresh-tokens-hourly": {
            "task": "app.workers.tasks.expire_refresh_tokens",
            "schedule": 60 * 60,
        },
        "check-low-stock-every-6h": {
            "task": "app.workers.tasks.check_low_stock",
            "schedule": 6 * 60 * 60,
        },
        "check-overdue-payments-daily": {
            "task": "app.workers.tasks.check_overdue_payments",
            "schedule": 24 * 60 * 60,
        },
        "check-production-delays-daily": {
            "task": "app.workers.tasks.check_production_delays",
            "schedule": 24 * 60 * 60,
        },
    },
)
