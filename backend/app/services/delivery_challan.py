"""Delivery Challan PDF — a printable document generated from an existing
ProductionStageChallan (ERP Upgrade §17). Not a generic report: this is a
document layout (From/To, product/process/lot, value), so it gets its
own template rather than reusing report_export.py's generic tabular
renderer — same approach as packing_slip.py.
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


def render_delivery_challan_pdf(
    company_name: str | None,
    challan: dict[str, Any],
    to_party: dict[str, Any],
    item: dict[str, Any],
) -> bytes:
    template = _env.get_template("delivery_challan.html")
    html = template.render(
        company_name=company_name,
        challan=challan,
        to_party=to_party,
        item=item,
        generated_at=datetime.now(timezone.utc),
    )
    return HTML(string=html).write_pdf()


def delivery_challan_filename(challan_number: str) -> str:
    safe = "".join(c if (c.isalnum() or c in ("-", "_")) else "_" for c in challan_number).strip("_")
    return f"DeliveryChallan_{safe or 'Challan'}.pdf"
