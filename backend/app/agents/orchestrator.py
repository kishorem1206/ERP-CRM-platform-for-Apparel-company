"""
LangGraph orchestrator for the Apparel ERP AI assistant.

Graph flow:
  START → orchestrator_node → [specialist routing] → confirmation_node → execute_node → response_node → END
"""
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.agents.state import ERPAgentState
from app.core.config import settings
from app.core.llm import get_client

SYSTEM_PROMPT = """You are an AI assistant for an Apparel Manufacturing ERP system.

You help users query data, create transactions, and manage their manufacturing business.

RULES YOU MUST FOLLOW:
1. Never invent prices, stock quantities, customer names, or any business data.
2. Never calculate GST, prices, or financial totals yourself — always use the provided tools.
3. For any write operation (creating orders, transferring stock, etc.) you MUST present a
   confirmation summary and wait for the user to say "yes", "confirm", or "proceed".
4. If the data needed to answer a question is not available through your tools, say so clearly.
5. Always respect the user's permission level — if a tool returns a permission error, inform
   the user that they don't have access to that action.

Available specialist domains: inventory, sales, purchase, production, finance, reports, master_data, crm.

When a user asks about stock levels, sales, production, or wants to create/update any record,
use the appropriate tool rather than answering from memory.
"""

INTENT_CATEGORIES = {
    "inventory": ["stock", "fabric", "yarn", "trim", "warehouse", "transfer", "balance", "ledger"],
    "sales": ["quotation", "order", "delivery", "invoice", "customer payment"],
    "purchase": ["purchase order", "po", "vendor", "receipt", "goods"],
    "production": ["lot", "cutting", "making", "sewing", "finishing", "production", "wip"],
    "finance": ["payment", "receipt", "outstanding", "overdue", "aging", "expense", "revenue", "income", "earning", "profit", "sales total", "total sales"],
    "reports": ["report", "summary", "analytics", "export"],
    "master_data": ["product", "customer", "vendor", "price list", "master"],
    "crm": ["lead", "opportunity", "follow up", "activity"],
}


def detect_intent(message: str) -> str:
    message_lower = message.lower()
    for intent, keywords in INTENT_CATEGORIES.items():
        if any(kw in message_lower for kw in keywords):
            return intent
    return "general"


async def orchestrator_node(state: ERPAgentState) -> dict:
    last_message = state["messages"][-1]
    content = last_message.content if hasattr(last_message, "content") else str(last_message)
    intent = detect_intent(content)
    return {"intent": intent, "specialist": intent}


async def inventory_agent_node(state: ERPAgentState) -> dict:
    from app.agents.specialist.inventory_agent import run_inventory_agent
    return await run_inventory_agent(state)


async def sales_agent_node(state: ERPAgentState) -> dict:
    from app.agents.specialist.sales_agent import run_sales_agent
    return await run_sales_agent(state)


async def production_agent_node(state: ERPAgentState) -> dict:
    from app.agents.specialist.production_agent import run_production_agent
    return await run_production_agent(state)


async def general_agent_node(state: ERPAgentState) -> dict:
    """Fallback: answer read-only questions directly via the configured LLM."""
    client = get_client()
    messages_payload = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + [
            {"role": m.type if m.type != "human" else "user", "content": m.content}
            for m in state["messages"]
            if hasattr(m, "type") and m.type in ("human", "assistant")
        ]
    )
    response = await client.chat.completions.create(
        model=settings.LLM_MODEL,
        max_tokens=settings.LLM_MAX_TOKENS,
        temperature=settings.LLM_TEMPERATURE,
        messages=messages_payload,
    )
    return {"response": response.choices[0].message.content or ""}


async def confirmation_node(state: ERPAgentState) -> dict:
    """If an action is pending confirmation, present it."""
    if state.get("pending_action"):
        summary = state["pending_action"].get("summary", "Confirm this action?")
        return {"response": f"{summary}\n\nType **confirm** to proceed or **cancel** to abort."}
    return {}


async def response_node(state: ERPAgentState) -> dict:
    """Final node — the response is already set by whichever node ran."""
    return {}


def route_to_specialist(state: ERPAgentState) -> Literal[
    "inventory_agent", "sales_agent", "production_agent", "general_agent"
]:
    specialist = state.get("specialist", "general")
    routing = {
        "inventory": "inventory_agent",
        "sales": "sales_agent",
        "production": "production_agent",
        "finance": "general_agent",
        "purchase": "general_agent",
    }
    return routing.get(specialist, "general_agent")


def build_erp_graph() -> StateGraph:
    graph = StateGraph(ERPAgentState)

    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("inventory_agent", inventory_agent_node)
    graph.add_node("sales_agent", sales_agent_node)
    graph.add_node("production_agent", production_agent_node)
    graph.add_node("general_agent", general_agent_node)
    graph.add_node("confirmation", confirmation_node)
    graph.add_node("response", response_node)

    graph.add_edge(START, "orchestrator")
    graph.add_conditional_edges("orchestrator", route_to_specialist)

    for specialist in ("inventory_agent", "sales_agent", "production_agent", "general_agent"):
        graph.add_edge(specialist, "confirmation")

    graph.add_edge("confirmation", "response")
    graph.add_edge("response", END)

    return graph.compile()


erp_graph = build_erp_graph()
