"""The agent loop: LLM ↔ tools until a final answer or iteration cap."""
import json
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AgentConversation, AgentMessage, User
from app.agents import llm, tools


def _append(db: Session, conversation: AgentConversation, **kwargs) -> AgentMessage:
    msg = AgentMessage(conversation_id=conversation.id, **kwargs)
    db.add(msg)
    return msg


def _history_dicts(conversation: AgentConversation, limit: int) -> List[Dict[str, Any]]:
    msgs = conversation.messages[-limit:] if limit > 0 else conversation.messages
    return [
        {
            "role": m.role,
            "content": m.content,
            "tool_calls": m.tool_calls,
            "tool_call_id": m.tool_call_id,
            "tool_name": m.tool_name,
        }
        for m in msgs
    ]


async def run_turn(
    db: Session,
    conversation: AgentConversation,
    user: User,
    user_text: str,
) -> List[AgentMessage]:
    """Run one user turn to completion; returns the messages it appended.

    Appends: the user message is persisted by the caller before this runs;
    this appends assistant/tool messages until the model answers without
    tool calls or `agent_max_iterations` is hit.
    """
    settings = get_settings()
    specs = tools.tool_specs()
    new_messages: List[AgentMessage] = []

    for _ in range(settings.agent_max_iterations):
        history = _history_dicts(conversation, settings.agent_max_history)
        # Include messages appended earlier in this same turn.
        history += [
            {
                "role": m.role,
                "content": m.content,
                "tool_calls": m.tool_calls,
                "tool_call_id": m.tool_call_id,
                "tool_name": m.tool_name,
            }
            for m in new_messages
        ]
        messages = llm.build_messages(history)

        assistant = await llm.chat_completion(messages, tools=specs)
        tool_calls = assistant.get("tool_calls") or []

        if not tool_calls:
            msg = _append(
                db, conversation,
                role="assistant",
                content=assistant.get("content") or "",
            )
            new_messages.append(msg)
            db.commit()
            return new_messages

        # Assistant asked for tools: persist the request, run each call.
        msg = _append(
            db, conversation,
            role="assistant",
            content=assistant.get("content") or "",
            tool_calls=json.dumps(tool_calls),
        )
        new_messages.append(msg)

        for call in tool_calls:
            fn = call.get("function", {})
            name = fn.get("name", "")
            try:
                arguments = json.loads(fn.get("arguments") or "{}")
            except ValueError:
                arguments = {}
            result = tools.execute_tool(
                db, user, conversation.organization_id, name, arguments
            )
            tool_msg = _append(
                db, conversation,
                role="tool",
                content=json.dumps(result),
                tool_call_id=call.get("id") or "",
                tool_name=name,
            )
            new_messages.append(tool_msg)

    # Iteration cap: ask the model for a closing answer without tools.
    history = _history_dicts(conversation, settings.agent_max_history)
    history += [
        {
            "role": m.role,
            "content": m.content,
            "tool_calls": m.tool_calls,
            "tool_call_id": m.tool_call_id,
            "tool_name": m.tool_name,
        }
        for m in new_messages
    ]
    messages = llm.build_messages(history)
    messages.append({
        "role": "system",
        "content": "Tool budget exhausted. Summarize what you found so far in one short answer.",
    })
    assistant = await llm.chat_completion(messages, tools=None)
    msg = _append(
        db, conversation,
        role="assistant",
        content=assistant.get("content") or "I couldn't complete the request within the tool budget.",
    )
    new_messages.append(msg)
    db.commit()
    return new_messages
