"""
Apparel ERP — Locust load test

Run:
    locust -f tests/load/locustfile.py --host http://localhost:8000 \
           --users 50 --spawn-rate 5 --run-time 2m

Required environment variables:
    ADMIN_SEED_PASSWORD   — password set when seeding the test database

Optional:
    LOAD_TEST_EMAIL       (default: admin@company.com)
"""
import json
import os
import random

from locust import HttpUser, between, task


_EMAIL = os.getenv("LOAD_TEST_EMAIL", "admin@company.com")
_PASSWORD = os.environ["ADMIN_SEED_PASSWORD"]


class ERPUser(HttpUser):
    wait_time = between(0.5, 2.0)
    access_token: str = ""

    def on_start(self):
        """Authenticate once per simulated user."""
        res = self.client.post(
            "/api/v1/auth/login",
            json={"email": _EMAIL, "password": _PASSWORD},
            name="/auth/login",
        )
        if res.status_code == 200:
            payload = res.json()
            data = payload.get("data", {})
            self.access_token = data.get("access_token", "")
        else:
            self.access_token = ""

    def _headers(self):
        return {"Authorization": f"Bearer {self.access_token}"}

    # ── Auth ────────────────────────────────────────────────────────────────

    @task(2)
    def get_me(self):
        self.client.get("/api/v1/auth/me", headers=self._headers(), name="/auth/me")

    # ── Products / Inventory ────────────────────────────────────────────────

    @task(8)
    def list_products(self):
        self.client.get(
            f"/api/v1/products?page=1&page_size=20&search={random.choice(['shirt', 'pant', 'fabric', ''])}",
            headers=self._headers(),
            name="/products (list)",
        )

    @task(5)
    def stock_balance(self):
        self.client.get(
            "/api/v1/inventory/stock-balance?page=1&page_size=20",
            headers=self._headers(),
            name="/inventory/stock-balance",
        )

    # ── Sales ────────────────────────────────────────────────────────────────

    @task(6)
    def list_sales_orders(self):
        self.client.get(
            "/api/v1/sales/orders?page=1&page_size=20",
            headers=self._headers(),
            name="/sales/orders (list)",
        )

    @task(4)
    def list_invoices(self):
        self.client.get(
            "/api/v1/sales/invoices?page=1&page_size=20",
            headers=self._headers(),
            name="/sales/invoices (list)",
        )

    # ── Purchase ─────────────────────────────────────────────────────────────

    @task(4)
    def list_purchase_orders(self):
        self.client.get(
            "/api/v1/purchase/orders?page=1&page_size=20",
            headers=self._headers(),
            name="/purchase/orders (list)",
        )

    # ── Production ────────────────────────────────────────────────────────────

    @task(3)
    def list_production_lots(self):
        self.client.get(
            "/api/v1/production/lots?page=1&page_size=20",
            headers=self._headers(),
            name="/production/lots (list)",
        )

    # ── Finance ──────────────────────────────────────────────────────────────

    @task(3)
    def list_customers(self):
        self.client.get(
            "/api/v1/sales/customers?page=1&page_size=20",
            headers=self._headers(),
            name="/sales/customers (list)",
        )

    # ── Notifications ─────────────────────────────────────────────────────────

    @task(2)
    def notification_count(self):
        self.client.get(
            "/api/v1/notifications/count",
            headers=self._headers(),
            name="/notifications/count",
        )

    # ── Reports ───────────────────────────────────────────────────────────────

    @task(1)
    def dashboard_report(self):
        self.client.get(
            "/api/v1/reports/dashboard",
            headers=self._headers(),
            name="/reports/dashboard",
        )

    # ── AI Agent (lower weight — expensive) ──────────────────────────────────

    @task(1)
    def ai_chat(self):
        self.client.post(
            "/api/v1/agents/chat",
            headers=self._headers(),
            json={"message": random.choice([
                "What is our current stock level?",
                "Show me pending sales orders",
                "Any overdue invoices?",
            ])},
            name="/agents/chat",
            timeout=30,
        )
