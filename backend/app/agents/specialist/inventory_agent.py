"""Inventory specialist — real-time stock queries via OpenAI-compatible tool calling."""
import json
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.db_tools import query_stock_balance, query_recent_transactions, to_json
from app.core.llm import run_agent_loop

SYSTEM = """You are the Inventory Specialist for an Apparel Manufacturing ERP.

You answer questions about:
- Current stock levels (fabric, yarn, trims, finished goods, accessories)
- Stock movements and transaction history
- Warehouse locations and distribution
- Low-stock situations

Always use the provided tools to fetch real data — never guess or invent quantities.
When reporting stock, include the warehouse and unit of measure.
"""

TOOLS = [
    {
        "name": "get_stock_balance",
        "description": "Get current on-hand stock quantity for products, grouped by warehouse. Use for questions like 'how much fabric do we have', 'what is the stock level', 'show me inventory'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Partial product name to filter. Leave empty to get all products."
                }
            }
        },
    },
    {
        "name": "get_recent_transactions",
        "description": "Get recent inventory movements (receipts, issues, transfers) for a product. Use for 'what happened to this stock', 'show movement history'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Partial product name to filter."
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of records to return (default 10, max 20)."
                }
            }
        },
    },
]


async def run_inventory_agent(
    message: str,
    history: list[dict],
    db: AsyncSession,
    company_id: str,
    permissions: list[str],
) -> str:
    async def exec_tool(name: str, args: dict) -> str:
        if name == "get_stock_balance":
            data = await query_stock_balance(db, company_id, args.get("product_name"))
            return to_json(data) if data else "No stock found."
        if name == "get_recent_transactions":
            data = await query_recent_transactions(
                db, company_id, args.get("product_name"), min(args.get("limit", 10), 20)
            )
            return to_json(data) if data else "No transactions found."
        return json.dumps({"error": f"Unknown tool: {name}"})

    return await run_agent_loop(
        system=SYSTEM, tools=TOOLS, history=history,
        message=message, exec_tool=exec_tool,
    )
