"""Agent conversations API: org-scoped chat with the agent runtime."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import (
    User, Organization, OrganizationMember, AgentConversation, AgentMessage,
)
from app.schemas.agents import (
    ConversationCreate, ConversationResponse, ConversationDetailResponse,
    MessageCreate, MessageSendResponse, MessageResponse, ToolInfo,
)
from app.api.auth import get_current_active_user
from app.agents import loop, tools

router = APIRouter()


def _get_membership(db: Session, user: User, org_id: UUID) -> OrganizationMember:
    member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user.id,
        )
        .first()
    )
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization",
        )
    return member


def _get_conversation(
    db: Session, conv_id: UUID, user: User
) -> AgentConversation:
    conv = (
        db.query(AgentConversation)
        .filter(
            AgentConversation.id == conv_id,
            AgentConversation.user_id == user.id,
        )
        .first()
    )
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return conv


def _to_detail(conv: AgentConversation) -> ConversationDetailResponse:
    return ConversationDetailResponse(
        id=conv.id,
        organization_id=conv.organization_id,
        user_id=conv.user_id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=len(conv.messages),
        messages=[
            MessageResponse(
                id=m.id,
                role=m.role,
                content=m.content,
                tool_name=m.tool_name,
                created_at=m.created_at,
            )
            for m in conv.messages
        ],
    )


@router.get("/tools", response_model=List[ToolInfo])
def list_tools():
    """List the tools the agent can call (read-only registry)."""
    return [
        ToolInfo(name=name, description=tools.get_tool(name).description)
        for name in tools.tool_names()
    ]


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    data: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Start a new agent conversation inside an organization."""
    _get_membership(db, current_user, data.organization_id)
    conv = AgentConversation(
        organization_id=data.organization_id,
        user_id=current_user.id,
        title=data.title,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return ConversationResponse(
        id=conv.id,
        organization_id=conv.organization_id,
        user_id=conv.user_id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=0,
    )


@router.get("/conversations", response_model=List[ConversationResponse])
def list_conversations(
    organization_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List the current user's conversations in an organization."""
    _get_membership(db, current_user, organization_id)
    convs = (
        db.query(AgentConversation)
        .filter(
            AgentConversation.organization_id == organization_id,
            AgentConversation.user_id == current_user.id,
        )
        .order_by(AgentConversation.updated_at.desc())
        .all()
    )
    counts = dict(
        db.query(AgentMessage.conversation_id, func.count(AgentMessage.id))
        .filter(AgentMessage.conversation_id.in_([c.id for c in convs]) if convs else [])
        .group_by(AgentMessage.conversation_id)
        .all()
    )
    return [
        ConversationResponse(
            id=c.id,
            organization_id=c.organization_id,
            user_id=c.user_id,
            title=c.title,
            created_at=c.created_at,
            updated_at=c.updated_at,
            message_count=counts.get(c.id, 0),
        )
        for c in convs
    ]


@router.get("/conversations/{conv_id}", response_model=ConversationDetailResponse)
def get_conversation(
    conv_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a conversation with its full message history."""
    conv = _get_conversation(db, conv_id, current_user)
    _get_membership(db, current_user, conv.organization_id)
    return _to_detail(conv)


@router.post("/conversations/{conv_id}/messages", response_model=MessageSendResponse)
async def send_message(
    conv_id: UUID,
    data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Send a user message and run the agent loop to completion."""
    conv = _get_conversation(db, conv_id, current_user)
    _get_membership(db, current_user, conv.organization_id)

    user_msg = AgentMessage(
        conversation_id=conv.id,
        role="user",
        content=data.content,
    )
    db.add(user_msg)
    db.commit()

    try:
        new_messages = await loop.run_turn(db, conv, current_user, data.content)
    except Exception as exc:
        # LLM failures surface as a clean API error, not a 500 stack.
        from app.agents.llm import LLMError
        if isinstance(exc, LLMError):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Agent backend error: {exc}",
            )
        raise

    return MessageSendResponse(
        conversation_id=conv.id,
        messages=[
            MessageResponse(
                id=m.id,
                role=m.role,
                content=m.content,
                tool_name=m.tool_name,
                created_at=m.created_at,
            )
            for m in new_messages
        ],
    )
