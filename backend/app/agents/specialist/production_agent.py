"""Production specialist — lot tracking and WIP queries via OpenAI-compatible tool calling."""
import json
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.db_tools import query_production_lots, to_json
from app.core.llm import run_agent_loop

SYSTEM = """You are the Production Specialist for an Apparel Manufacturing ERP.

You help with:
- Production lot status and progress tracking
- WIP (Work In Progress) monitoring
- Delivery timeline checking
- Stage-wise completion (cutting, making, finishing, QC, packing)

Use the provided tools. Never guess lot numbers, quantities, or delivery dates.
"""

TOOLS = [
    {
        "name": "get_production_lots",
        "description": "Get production lot list. Filter by status to see WIP, completed, or delayed lots. Status values: draft, planned, approved, in_production, qc, packing, completed, cancelled.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Status filter: draft, planned, approved, in_production, qc, packing, completed, cancelled"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of records to return (default 10)"
                }
            }
        },
    },
]


async def run_production_agent(
    message: str,
    history: list[dict],
    db: AsyncSession,
    company_id: str,
    permissions: list[str],
) -> str:
    async def exec_tool(name: str, args: dict) -> str:
        if name == "get_production_lots":
            data = await query_production_lots(
                db, company_id,
                status=args.get("status"),
                limit=min(args.get("limit", 10), 20),
            )
            return to_json(data) if data else "No production lots found."
        return json.dumps({"error": f"Unknown tool: {name}"})

    return await run_agent_loop(
        system=SYSTEM, tools=TOOLS, history=history,
        message=message, exec_tool=exec_tool,
    )
