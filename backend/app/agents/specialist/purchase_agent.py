"""Purchase specialist — PO status and vendor payment queries."""
import json
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.db_tools import query_purchase_orders, query_vendor_outstanding, to_json
from app.core.llm import run_agent_loop

SYSTEM = """You are the Purchase Specialist for an Apparel Manufacturing ERP.

You help with:
- Purchase order status (open, approved, received, closed)
- Goods receipt tracking (GRNs)
- Vendor payment and outstanding payables
- Pending deliveries from vendors

Use tools to get real data. Never guess PO numbers or amounts.
"""

TOOLS = [
    {
        "name": "get_purchase_orders",
        "description": "Get recent purchase orders. Filter by status: draft, approved, partial, received, cancelled.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Status filter: draft, approved, partial, received, cancelled"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of records (default 10)"
                }
            }
        },
    },
    {
        "name": "get_vendor_outstanding",
        "description": "Get outstanding amounts payable to vendors.",
        "input_schema": {
            "type": "object",
            "properties": {}
        },
    },
]


async def run_purchase_agent(
    message: str,
    history: list[dict],
    db: AsyncSession,
    company_id: str,
    permissions: list[str],
) -> str:
    async def exec_tool(name: str, args: dict) -> str:
        if name == "get_purchase_orders":
            data = await query_purchase_orders(
                db, company_id,
                status=args.get("status"),
                limit=min(args.get("limit", 10), 20),
            )
            return to_json(data) if data else "No purchase orders found."
        if name == "get_vendor_outstanding":
            data = await query_vendor_outstanding(db, company_id)
            return to_json(data) if data else "No vendor outstanding amounts."
        return json.dumps({"error": f"Unknown tool: {name}"})

    return await run_agent_loop(
        system=SYSTEM, tools=TOOLS, history=history,
        message=message, exec_tool=exec_tool,
    )
