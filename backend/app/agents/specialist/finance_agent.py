"""Finance specialist — receivables, payables, and outstanding queries."""
import json
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.db_tools import query_outstanding_invoices, query_vendor_outstanding, query_revenue_summary, to_json
from app.core.llm import run_agent_loop

SYSTEM = """You are the Finance Specialist for an Apparel Manufacturing ERP.

You help with:
- Customer receivables (outstanding invoices, overdue amounts)
- Vendor payables (what we owe suppliers)
- Payment status tracking
- Aging analysis

Use the provided tools to fetch real data. Present amounts in Indian Rupees (₹).
Never guess financial figures.
"""

TOOLS = [
    {
        "name": "get_customer_outstanding",
        "description": "Get unpaid or partially paid customer invoices. Use for 'receivables', 'what customers owe us', 'overdue invoices'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_name": {
                    "type": "string",
                    "description": "Partial customer name to filter"
                }
            }
        },
    },
    {
        "name": "get_vendor_outstanding",
        "description": "Get unpaid vendor bills. Use for 'payables', 'what we owe vendors/suppliers', 'vendor outstanding'.",
        "input_schema": {
            "type": "object",
            "properties": {}
        },
    },
    {
        "name": "get_revenue_summary",
        "description": "Get total revenue (invoiced amount) from sales. Use for 'how much revenue', 'total sales', 'income', 'earnings'. Can be grouped by month or by customer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "description": "Grouping: 'month' for month-wise breakdown, 'customer' for customer-wise, or omit for overall total."
                }
            }
        },
    },
]


async def run_finance_agent(
    message: str,
    history: list[dict],
    db: AsyncSession,
    company_id: str,
    permissions: list[str],
) -> str:
    async def exec_tool(name: str, args: dict) -> str:
        if name == "get_customer_outstanding":
            data = await query_outstanding_invoices(db, company_id, args.get("customer_name"))
            return to_json(data) if data else "No outstanding invoices."
        if name == "get_vendor_outstanding":
            data = await query_vendor_outstanding(db, company_id)
            return to_json(data) if data else "No vendor outstanding amounts."
        if name == "get_revenue_summary":
            data = await query_revenue_summary(db, company_id, args.get("period"))
            return to_json(data) if data else "No invoice data found."
        return json.dumps({"error": f"Unknown tool: {name}"})

    return await run_agent_loop(
        system=SYSTEM, tools=TOOLS, history=history,
        message=message, exec_tool=exec_tool,
    )
