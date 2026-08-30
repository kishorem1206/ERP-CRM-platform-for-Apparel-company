from typing import Annotated, Any
from uuid import UUID

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class ERPAgentState(TypedDict):
    # Conversation
    messages: Annotated[list, add_messages]
    conversation_id: str

    # Auth context (injected at graph entry, never modified by agents)
    user_id: str
    company_id: str
    permissions: list[str]

    # Routing
    intent: str | None          # detected intent category
    specialist: str | None      # which specialist agent to invoke

    # Domain data fetched this turn (read-only in agents, set by tools)
    context: dict[str, Any]

    # Write operations: pending confirmation
    pending_action: dict[str, Any] | None
    confirmed: bool             # True after user confirms a write action

    # Final response assembled by response_node
    response: str | None
    error: str | None
