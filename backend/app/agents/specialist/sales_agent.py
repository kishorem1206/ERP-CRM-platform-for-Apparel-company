"""Sales specialist — order and invoice queries via OpenAI-compatible tool calling."""
import json
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.db_tools import query_sales_orders, query_outstanding_invoices, to_json
from app.core.llm import run_agent_loop

SYSTEM = """You are the Sales Specialist for an Apparel Manufacturing ERP.

You help with:
- Sales order status and tracking
- Customer outstanding invoices and payment status
- Delivery schedules and delays
- Customer-wise sales summaries

Use the provided tools to fetch real data. Never invent order numbers, amounts, or customer names.
"""

TOOLS = [
    {
        "name": "get_sales_orders",
        "description": "Get recent sales orders. Filter by status (draft, confirmed, dispatched, delivered, cancelled) or customer name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Order status filter: draft, confirmed, dispatched, delivered, cancelled"
                },
                "customer_name": {
                    "type": "string",
                    "description": "Partial customer name to filter"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of records (default 10)"
                }
            }
        },
    },
    {
        "name": "get_outstanding_invoices",
        "description": "Get unpaid or partially paid invoices. Use for 'what is outstanding', 'overdue invoices', 'customer receivables'.",
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
]


async def run_sales_agent(
    message: str,
    history: list[dict],
    db: AsyncSession,
    company_id: str,
    permissions: list[str],
) -> str:
    async def exec_tool(name: str, args: dict) -> str:
        if name == "get_sales_orders":
            data = await query_sales_orders(
                db, company_id,
                status=args.get("status"),
                customer_name=args.get("customer_name"),
                limit=min(args.get("limit", 10), 20),
            )
            return to_json(data) if data else "No sales orders found."
        if name == "get_outstanding_invoices":
            data = await query_outstanding_invoices(db, company_id, args.get("customer_name"))
            return to_json(data) if data else "No outstanding invoices found."
        return json.dumps({"error": f"Unknown tool: {name}"})

    return await run_agent_loop(
        system=SYSTEM, tools=TOOLS, history=history,
        message=message, exec_tool=exec_tool,
    )
