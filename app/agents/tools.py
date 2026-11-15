"""Tool registry for the org-scoped agent.

Tools are read-only for now: they expose the same data the REST API
serves, scoped to the conversation's organization and the calling user.
Each tool receives (db, user, org_id, args) and must re-check membership
or role — the agent never bypasses the authorization the API enforces.
"""
import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import (
    User, Organization, OrganizationMember, Invitation, OrganizationRole,
)


@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema object
    func: Callable[[Session, User, UUID, Dict[str, Any]], Dict[str, Any]]

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


def execute_tool(db: Session, user: User, org_id: UUID, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Run a registered tool, returning a JSON-safe result or error dict."""
    tool = get_tool(name)
    if tool is None:
        return {"ok": False, "error": f"Unknown tool: {name}"}
    try:
        result = tool.func(db, user, org_id, arguments or {})
        return {"ok": True, "result": result}
    except PermissionError as exc:
        return {"ok": False, "error": str(exc)}
    except LookupError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:  # tool failures must not kill the loop
        return {"ok": False, "error": f"Tool {name} failed: {exc}"}
