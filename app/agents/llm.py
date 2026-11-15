"""OpenAI-compatible chat client for the agent loop.

Any endpoint that speaks POST {base}/chat/completions works — Ollama's
/v1 compatibility layer is the default. No vendor SDK: plain httpx.
"""
import json
from typing import Any, Dict, List, Optional

import httpx

from app.config import get_settings

SYSTEM_PROMPT = (
    "You are the StreamWeave assistant for one organization. "
    "Answer questions about the organization, its members and pending "
    "invitations using the available tools. Most tools are read-only. "
    "Some tools change state: calling one only creates a pending action "
    "that a human must approve — it does NOT perform the change. When a "
    "tool result contains 'pending_confirmation', tell the user the "
    "action is awaiting their approval and never claim it was completed. "
    "If a tool result shows an error, explain it plainly. Keep answers "
    "concise."
)


class LLMError(Exception):
    """Raised when the LLM endpoint fails or returns an unusable body."""


def _endpoint() -> str:
    settings = get_settings()
    return settings.agent_llm_base_url.rstrip("/") + "/chat/completions"


def _headers() -> Dict[str, str]:
    settings = get_settings()
    headers = {"Content-Type": "application/json"}
    if settings.agent_llm_api_key:
        headers["Authorization"] = f"Bearer {settings.agent_llm_api_key}"
    return headers


async def chat_completion(
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Call the chat-completions endpoint; returns the assistant `message` dict.

    The returned dict may contain `tool_calls` — pass it back verbatim in
    the next request's messages to continue the tool loop.
    """
    settings = get_settings()
    payload: Dict[str, Any] = {
        "model": settings.agent_llm_model,
        "messages": messages,
        "temperature": 0.3,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(_endpoint(), json=payload, headers=_headers())
    except httpx.HTTPError as exc:
        raise LLMError(f"LLM request failed: {exc}") from exc

    if resp.status_code != 200:
        raise LLMError(f"LLM returned {resp.status_code}: {resp.text[:300]}")

    try:
        body = resp.json()
        message = body["choices"][0]["message"]
    except (ValueError, KeyError, IndexError) as exc:
        raise LLMError(f"Malformed LLM response: {resp.text[:300]}") from exc

    return message


def build_messages(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert stored AgentMessage rows into OpenAI chat messages.

    `history` items: dicts with role/content/tool_calls/tool_call_id/
    tool_name. Tool calls are replayed with their JSON arguments.
    """
    messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in history:
        role = m["role"]
        if role == "tool":
            messages.append({
                "role": "tool",
                "tool_call_id": m.get("tool_call_id") or "",
                "content": m.get("content") or "",
            })
            continue
        msg: Dict[str, Any] = {"role": role, "content": m.get("content")}
        if m.get("tool_calls"):
            try:
                msg["tool_calls"] = json.loads(m["tool_calls"])
            except (ValueError, TypeError):
                pass
        messages.append(msg)
    return messages
