"""Agent conversations API: org-scoped chat with the agent runtime."""
import json
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.database import get_db
from app.models import (
    User, Organization, OrganizationMember, OrganizationRole,
    AgentConversation, AgentMessage, AgentPendingAction,
)
from app.schemas.agents import (
    ConversationCreate, ConversationResponse, ConversationDetailResponse,
    MessageCreate, MessageSendResponse, MessageResponse, ToolInfo,
    PendingActionResponse,
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


# --- Pending write actions (human confirmation) ---------------------------


def _action_to_response(a: AgentPendingAction) -> PendingActionResponse:
    return PendingActionResponse(
        id=a.id,
        conversation_id=a.conversation_id,
        organization_id=a.organization_id,
        user_id=a.user_id,
        tool_name=a.tool_name,
        arguments=json.loads(a.arguments or "{}"),
        status=a.status,
        result=json.loads(a.result) if a.result else None,
        error=a.error,
        expires_at=a.expires_at,
        created_at=a.created_at,
        resolved_at=a.resolved_at,
        resolved_by=a.resolved_by,
    )


def _admin_org_ids(db: Session, user: User) -> List[UUID]:
    """Orgs where the user holds OWNER or ADMIN — action delegation scope."""
    return [
        m.organization_id
        for m in db.query(OrganizationMember)
        .filter(
            OrganizationMember.user_id == user.id,
            OrganizationMember.role.in_(
                [OrganizationRole.OWNER, OrganizationRole.ADMIN]
            ),
        )
        .all()
    ]


def _get_action(db: Session, action_id: UUID, user: User) -> AgentPendingAction:
    """Fetch an action the caller may see: its proposer, or an org admin.

    Org OWNER/ADMIN members can see and resolve actions proposed by other
    members of the same org (delegated confirmation); everyone else gets
    the same 404 as a missing action so existence isn't leaked.
    """
    action = db.query(AgentPendingAction).filter(
        AgentPendingAction.id == action_id
    ).first()
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found",
        )
    if action.user_id == user.id:
        return action
    member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == action.organization_id,
            OrganizationMember.user_id == user.id,
        )
        .first()
    )
    if member and member.role in (OrganizationRole.OWNER, OrganizationRole.ADMIN):
        return action
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Action not found",
    )


@router.get("/actions", response_model=List[PendingActionResponse])
def list_actions(
    conversation_id: Optional[UUID] = None,
    action_status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List actions visible to the caller: their own, plus — for org
    OWNER/ADMIN members — every action in those orgs (delegated
    confirmation and audit)."""
    query = db.query(AgentPendingAction).filter(
        or_(
            AgentPendingAction.user_id == current_user.id,
            AgentPendingAction.organization_id.in_(_admin_org_ids(db, current_user)),
        )
    )
    if conversation_id:
        query = query.filter(AgentPendingAction.conversation_id == conversation_id)
    if action_status:
        query = query.filter(AgentPendingAction.status == action_status)
    actions = query.order_by(AgentPendingAction.created_at.desc()).all()
    return [_action_to_response(a) for a in actions]


@router.post("/actions/{action_id}/approve", response_model=PendingActionResponse)
def approve_action(
    action_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Approve a pending write action — executes it under the caller's identity."""
    action = _get_action(db, action_id, current_user)
    _get_membership(db, current_user, action.organization_id)

    if action.status == "pending" and action.is_expired():
        action.status = "expired"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Action expired before approval",
        )
    if action.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Action is already {action.status}",
        )

    result = tools.run_approved_action(
        db,
        current_user,
        action.organization_id,
        action.tool_name,
        json.loads(action.arguments or "{}"),
    )
    action.resolved_at = datetime.utcnow()
    action.resolved_by = current_user.id
    if result.get("ok"):
        action.status = "executed"
        action.result = json.dumps(result.get("result"))
    else:
        action.status = "failed"
        action.error = result.get("error")
    db.commit()
    db.refresh(action)
    return _action_to_response(action)


@router.post("/actions/{action_id}/reject", response_model=PendingActionResponse)
def reject_action(
    action_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Reject a pending write action — it is never executed."""
    action = _get_action(db, action_id, current_user)
    _get_membership(db, current_user, action.organization_id)

    if action.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Action is already {action.status}",
        )
    action.status = "rejected"
    action.resolved_at = datetime.utcnow()
    action.resolved_by = current_user.id
    db.commit()
    db.refresh(action)
    return _action_to_response(action)
