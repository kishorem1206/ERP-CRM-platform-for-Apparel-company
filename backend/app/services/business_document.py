"""Printable business documents (quotation, order, challan, invoice, PO, GRN).

Builds a plain dict from the existing API output models and renders one shared
A4 layout. The dict is the only contract between the endpoints and the template.
"""
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=select_autoescape(["html"]))


def inr(value: Any) -> str:
    amount = Decimal(str(value or 0)).quantize(Decimal("0.01"))
    sign = "-" if amount < 0 else ""
    integer, fraction = f"{abs(amount):.2f}".split(".")
    if len(integer) > 3:
        head, tail = integer[:-3], integer[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        integer = ",".join(groups + [tail])
    return f"{sign}₹{integer}.{fraction}"


def qty(value: Any) -> str:
    d = Decimal(str(value or 0)).normalize()
    return format(d, "f")


def date_text(value: Any) -> str:
    if not value:
        return "—"
    if isinstance(value, datetime):
        value = value.date()
    return value.strftime("%d %b %Y")


def render_business_document_pdf(company: dict[str, Any], doc: dict[str, Any]) -> bytes:
    html = _env.get_template("business_document.html").render(
        company=company,
        doc=doc,
        generated_at=datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC"),
    )
    return HTML(string=html).write_pdf()


def document_filename(title: str, number: str) -> str:
    safe = "".join(c if (c.isalnum() or c in ("-", "_")) else "_" for c in f"{title}_{number}").strip("_")
    return f"{safe or 'document'}.pdf"
