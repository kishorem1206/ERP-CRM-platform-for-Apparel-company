import uuid
from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.history import load_history, save_history
from app.agents.orchestrator import detect_intent
from app.api.v1.deps import AuthUser, DBSession
from app.core.config import settings
from app.core.llm import get_client

router = APIRouter()

GENERAL_SYSTEM = (
    "You are an AI assistant for an Apparel Manufacturing ERP system. "
    "Help users understand ERP concepts, workflows, and navigate the system. "
    "If the user is asking about specific data (stock, orders, invoices, revenue), "
    "let them know they should phrase the question more specifically so the right "
    "specialist can answer (Inventory, Sales, Production, Finance, Purchase)."
)


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    confirmed: bool = False


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    requires_confirmation: bool = False
    pending_action: dict | None = None


async def _dispatch(
    intent: str,
    message: str,
    history: list[dict],
    db,
    company_id: str,
    permissions: list[str],
) -> str:
    common = dict(message=message, history=history, db=db, company_id=company_id, permissions=permissions)

    if intent == "inventory":
        from app.agents.specialist.inventory_agent import run_inventory_agent
        return await run_inventory_agent(**common)

    if intent == "sales":
        from app.agents.specialist.sales_agent import run_sales_agent
        return await run_sales_agent(**common)

    if intent == "production":
        from app.agents.specialist.production_agent import run_production_agent
        return await run_production_agent(**common)

    if intent in ("finance", "revenue"):
        from app.agents.specialist.finance_agent import run_finance_agent
        return await run_finance_agent(**common)

    if intent == "purchase":
        from app.agents.specialist.purchase_agent import run_purchase_agent
        return await run_purchase_agent(**common)

    # General fallback via OpenAI-compatible client
    client = get_client()
    msgs = (
        [{"role": "system", "content": GENERAL_SYSTEM}]
        + list(history)
        + [{"role": "user", "content": message}]
    )
    resp = await client.chat.completions.create(
        model=settings.LLM_MODEL,
        max_tokens=settings.LLM_MAX_TOKENS,
        temperature=settings.LLM_TEMPERATURE,
        messages=msgs,
    )
    return resp.choices[0].message.content or "I couldn't process that request. Please try again."


@router.post("/agents/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, user: AuthUser, db: DBSession):
    conversation_id = body.conversation_id or str(uuid.uuid4())

    history = await load_history(conversation_id)
    intent = detect_intent(body.message)

    response_text = await _dispatch(
        intent=intent,
        message=body.message,
        history=history,
        db=db,
        company_id=str(user.company_id),
        permissions=user.permissions,
    )

    history.append({"role": "user", "content": body.message})
    history.append({"role": "assistant", "content": response_text})
    await save_history(conversation_id, history)

    return ChatResponse(
        response=response_text,
        conversation_id=conversation_id,
    )
