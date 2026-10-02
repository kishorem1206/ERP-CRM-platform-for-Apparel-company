"""Generic tabular PDF export for any Reports Hub page.

Renders exactly the rows/columns the browser already fetched and displays —
the frontend posts its already-rendered table data here, so the PDF can
never show numbers that disagree with the on-screen report. No business
calculation happens in this module.
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


def render_report_table_pdf(
    company_name: str | None,
    title: str,
    subtitle: str | None,
    columns: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    totals: list[dict[str, Any]],
) -> bytes:
    template = _env.get_template("report_table.html")
    html = template.render(
        company_name=company_name,
        title=title,
        subtitle=subtitle,
        columns=columns,
        rows=rows,
        totals=totals,
        generated_at=datetime.now(timezone.utc),
    )
    return HTML(string=html).write_pdf()


def report_pdf_filename(title: str) -> str:
    safe = "".join(c if (c.isalnum() or c in ("-", "_")) else "_" for c in title).strip("_")
    return f"{safe or 'Report'}.pdf"
