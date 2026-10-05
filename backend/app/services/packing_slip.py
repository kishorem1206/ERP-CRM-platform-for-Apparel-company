"""Packing Slip PDF — a printable document generated from an existing
Delivery record (ERP Upgrade §4). Not a generic report: this is a
document layout (customer block, SO reference, packing/dispatch info),
so it gets its own template rather than reusing report_export.py's
generic tabular renderer.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def render_packing_slip_pdf(
    company_name: str | None,
    delivery: dict[str, Any],
    sales_order: dict[str, Any] | None,
    customer: dict[str, Any] | None,
    items: list[dict[str, Any]],
) -> bytes:
    template = _env.get_template("packing_slip.html")
    html = template.render(
        company_name=company_name,
        delivery=delivery,
        sales_order=sales_order,
        customer=customer,
        items=items,
        generated_at=datetime.now(timezone.utc),
    )
    return HTML(string=html).write_pdf()


def packing_slip_filename(delivery_number: str) -> str:
    safe = "".join(c if (c.isalnum() or c in ("-", "_")) else "_" for c in delivery_number).strip("_")
    return f"PackingSlip_{safe or 'Delivery'}.pdf"
