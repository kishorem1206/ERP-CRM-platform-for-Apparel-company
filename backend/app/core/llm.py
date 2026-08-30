"""
Shared OpenAI-compatible LLM client.

Converts Anthropic tool-definition format (input_schema) to OpenAI function-calling
format (parameters) so all agents can share one adapter with any OpenAI-compat provider.
"""
import json
from openai import AsyncOpenAI
from app.core.config import settings


def get_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.effective_llm_api_key,
        base_url=settings.effective_llm_base_url or None,
    )


def to_openai_tools(anthropic_tools: list[dict]) -> list[dict]:
    """Convert Anthropic-style tool defs (input_schema) to OpenAI function format."""
    result = []
    for t in anthropic_tools:
        result.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
            },
        })
    return result


async def run_agent_loop(
    *,
    system: str,
    tools: list[dict],
    history: list[dict],
    message: str,
    exec_tool,  # async callable(name, args_dict) -> str
    max_rounds: int = 6,
    max_tokens: int = 1024,
) -> str:
    """
    Generic OpenAI-compatible agentic loop with tool calling.

    Handles the full round-trip: user message → model → tool call → tool result → model,
    repeated up to max_rounds times.
    """
    client = get_client()
    oai_tools = to_openai_tools(tools)

    messages: list[dict] = (
        [{"role": "system", "content": system}]
        + list(history)
        + [{"role": "user", "content": message}]
    )

    for _ in range(max_rounds):
        resp = await client.chat.completions.create(
            model=settings.LLM_MODEL,
            max_tokens=max_tokens,
            temperature=settings.LLM_TEMPERATURE,
            tools=oai_tools,
            messages=messages,
        )

        choice = resp.choices[0]
        msg = choice.message

        if choice.finish_reason == "stop" or not msg.tool_calls:
            return msg.content or "Done."

        # Append assistant message with tool_calls
        messages.append(msg.model_dump(exclude_unset=True))

        # Execute each tool call and append results
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}
            result = await exec_tool(tc.function.name, args)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    return "I was unable to complete the query. Please try rephrasing your question."
