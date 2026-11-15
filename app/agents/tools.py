"""Tool registry for the org-scoped agent.

Read tools execute inside the LLM loop. Write tools
(`requires_confirmation=True`) never run there: `execute_tool` parks
them as `AgentPendingAction` rows and the API's approve endpoint runs
them later under the approving user's identity — the agent proposes,
a human disposes.

Each tool receives (db, user, org_id, args) and must re-check membership
or role — the agent never bypasses the authorization the API enforces.
"""
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import (
    User, Organization, OrganizationMember, Invitation, OrganizationRole,
    AgentPendingAction,
)
from app.utils.auth import generate_invitation_token


@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema object
    func: Callable[[Session, User, UUID, Dict[str, Any]], Dict[str, Any]]
    requires_confirmation: bool = False

    def spec(self) -> Dict[str, Any]:
        """OpenAI-compatible tool specification."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


def _require_member(db: Session, user: User, org_id: UUID) -> OrganizationMember:
    member = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user.id,
        )
        .first()
    )
    if not member:
        raise PermissionError("Not a member of this organization")
    return member


def _require_admin(db: Session, user: User, org_id: UUID) -> OrganizationMember:
    member = _require_member(db, user, org_id)
    if member.role not in (OrganizationRole.OWNER, OrganizationRole.ADMIN):
        raise PermissionError("Insufficient permissions")
    return member


def _org_or_404(db: Session, org_id: UUID) -> Organization:
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise LookupError("Organization not found")
    return org


def list_org_members(db: Session, user: User, org_id: UUID, args: Dict[str, Any]) -> Dict[str, Any]:
    _require_member(db, user, org_id)
    org = _org_or_404(db, org_id)
    members = (
        db.query(OrganizationMember)
        .filter(OrganizationMember.organization_id == org_id)
        .all()
    )
    return {
        "organization": {"id": str(org.id), "name": org.name, "slug": org.slug},
        "members": [
            {
                "user_id": str(m.user_id),
                "role": m.role.value,
                "email": m.user.email if m.user else None,
                "full_name": m.user.full_name if m.user else None,
                "joined_at": m.joined_at.isoformat() if m.joined_at else None,
            }
            for m in members
        ],
    }


def get_organization_info(db: Session, user: User, org_id: UUID, args: Dict[str, Any]) -> Dict[str, Any]:
    _require_member(db, user, org_id)
    org = _org_or_404(db, org_id)
    member_count = (
        db.query(OrganizationMember)
        .filter(OrganizationMember.organization_id == org_id)
        .count()
    )
    return {
        "id": str(org.id),
        "name": org.name,
        "slug": org.slug,
        "industry": org.industry.value,
        "size": org.size.value,
        "description": org.description,
        "member_count": member_count,
        "created_at": org.created_at.isoformat() if org.created_at else None,
    }


def list_pending_invitations(db: Session, user: User, org_id: UUID, args: Dict[str, Any]) -> Dict[str, Any]:
    _require_admin(db, user, org_id)
    invitations = (
        db.query(Invitation)
        .filter(
            Invitation.organization_id == org_id,
            Invitation.accepted_at.is_(None),
        )
        .all()
    )
    return {
        "invitations": [
            {
                "email": i.email,
                "role": i.role.value,
                "expires_at": i.expires_at.isoformat() if i.expires_at else None,
                "expired": i.is_expired(),
            }
            for i in invitations
        ]
    }


def list_my_organizations(db: Session, user: User, org_id: UUID, args: Dict[str, Any]) -> Dict[str, Any]:
    """Org-agnostic: lists every org the user belongs to."""
    rows = (
        db.query(Organization, OrganizationMember.role)
        .join(OrganizationMember, Organization.id == OrganizationMember.organization_id)
        .filter(OrganizationMember.user_id == user.id)
        .all()
    )
    return {
        "organizations": [
            {
                "id": str(org.id),
                "name": org.name,
                "slug": org.slug,
                "industry": org.industry.value,
                "role": role.value,
            }
            for org, role in rows
        ]
    }


def invite_org_member(db: Session, user: User, org_id: UUID, args: Dict[str, Any]) -> Dict[str, Any]:
    """Create an organization invitation. Requires admin/owner and human
    confirmation — runs only from the approve endpoint, never in-loop."""
    _require_admin(db, user, org_id)
    _org_or_404(db, org_id)

    email = (args.get("email") or "").strip().lower()
    role_raw = (args.get("role") or "viewer").strip().lower()
    if not email or "@" not in email:
        raise ValueError("A valid email is required")
    try:
        role = OrganizationRole(role_raw)
    except ValueError:
        raise ValueError(f"Unknown role: {role_raw}")
    # Agents may only grant non-privileged roles.
    if role not in (OrganizationRole.EDITOR, OrganizationRole.VIEWER):
        raise ValueError(f"Agents may not grant role: {role_raw}")

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        existing_member = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == existing_user.id,
            )
            .first()
        )
        if existing_member:
            raise ValueError("User is already a member of this organization")

    pending = (
        db.query(Invitation)
        .filter(
            Invitation.email == email,
            Invitation.organization_id == org_id,
            Invitation.accepted_at.is_(None),
        )
        .first()
    )
    if pending and not pending.is_expired():
        raise ValueError("A pending invitation already exists for this email")

    invitation = Invitation(
        email=email,
        organization_id=org_id,
        role=role,
        token=generate_invitation_token(),
        invited_by=user.id,
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return {
        "invitation_id": str(invitation.id),
        "email": invitation.email,
        "role": invitation.role.value,
        "expires_at": invitation.expires_at.isoformat() if invitation.expires_at else None,
    }


_REGISTRY: Dict[str, Tool] = {}


def register(tool: Tool) -> Tool:
    _REGISTRY[tool.name] = tool
    return tool


def get_tool(name: str) -> Optional[Tool]:
    return _REGISTRY.get(name)


def tool_specs() -> List[Dict[str, Any]]:
    return [t.spec() for t in _REGISTRY.values()]


def tool_names() -> List[str]:
    return sorted(_REGISTRY)


# --- Built-in tools -------------------------------------------------------

register(Tool(
    name="list_org_members",
    description="List all members of the current organization with their roles.",
    parameters={"type": "object", "properties": {}, "required": []},
    func=list_org_members,
))

register(Tool(
    name="get_organization_info",
    description="Get details about the current organization (name, industry, size, member count).",
    parameters={"type": "object", "properties": {}, "required": []},
    func=get_organization_info,
))

register(Tool(
    name="list_pending_invitations",
    description="List pending (not yet accepted) invitations for the current organization. Requires admin or owner role.",
    parameters={"type": "object", "properties": {}, "required": []},
    func=list_pending_invitations,
))

register(Tool(
    name="list_my_organizations",
    description="List every organization the current user belongs to, with the user's role in each.",
    parameters={"type": "object", "properties": {}, "required": []},
    func=list_my_organizations,
))

register(Tool(
    name="invite_org_member",
    description="Invite a person to the current organization by email. "
                "REQUIRES HUMAN CONFIRMATION: the call only creates a "
                "pending action; a user must approve it before the "
                "invitation is sent. Requires admin or owner role.",
    parameters={
        "type": "object",
        "properties": {
            "email": {"type": "string", "description": "Email address to invite"},
            "role": {
                "type": "string",
                "description": "Role to grant: editor or viewer",
                "enum": ["editor", "viewer"],
            },
        },
        "required": ["email"],
    },
    func=invite_org_member,
    requires_confirmation=True,
))


def execute_tool(
    db: Session,
    user: User,
    org_id: UUID,
    name: str,
    arguments: Dict[str, Any],
    conversation_id: Optional[UUID] = None,
) -> Dict[str, Any]:
    """Run a registered tool, returning a JSON-safe result or error dict.

    Tools flagged `requires_confirmation` are never executed here: a
    pending action is persisted (needs `conversation_id`) and the result
    tells the model (and the user) that human approval is required.
    """
    tool = get_tool(name)
    if tool is None:
        return {"ok": False, "error": f"Unknown tool: {name}"}
    if tool.requires_confirmation:
        if conversation_id is None:
            return {"ok": False, "error": "Confirmation actions require a conversation context"}
        action = AgentPendingAction(
            conversation_id=conversation_id,
            organization_id=org_id,
            user_id=user.id if user else None,
            tool_name=name,
            arguments=json.dumps(arguments or {}),
            status="pending",
            expires_at=datetime.utcnow() + AgentPendingAction.ttl(),
        )
        db.add(action)
        db.commit()
        db.refresh(action)
        return {
            "ok": True,
            "pending_confirmation": {
                "action_id": str(action.id),
                "tool": name,
                "description": tool.description,
                "arguments": arguments or {},
                "expires_at": action.expires_at.isoformat(),
                "instruction": "This action requires human approval. "
                               "Tell the user it is pending and can be "
                               "approved via POST /api/agents/actions/"
                               f"{action.id}/approve.",
            },
        }
    return _run_tool(db, user, org_id, tool, arguments or {})


def _run_tool(db: Session, user: User, org_id: UUID, tool: Tool, arguments: Dict[str, Any]) -> Dict[str, Any]:
    try:
        result = tool.func(db, user, org_id, arguments)
        return {"ok": True, "result": result}
    except PermissionError as exc:
        return {"ok": False, "error": str(exc)}
    except LookupError as exc:
        return {"ok": False, "error": str(exc)}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:  # tool failures must not kill the loop
        return {"ok": False, "error": f"Tool {tool.name} failed: {exc}"}


def run_approved_action(
    db: Session, user: User, org_id: UUID, name: str, arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute a write tool at approval time — the human-confirmed path.

    The tool's own membership/role checks still run, so approval never
    grants more than the approver already has.
    """
    tool = get_tool(name)
    if tool is None:
        return {"ok": False, "error": f"Unknown tool: {name}"}
    return _run_tool(db, user, org_id, tool, arguments or {})
