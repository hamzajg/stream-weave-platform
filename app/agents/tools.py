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
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.api.workflows import _unique_slug, generate_slug
from app.models import (
    User, Organization, OrganizationMember, Invitation, OrganizationRole,
    AgentPendingAction, Workflow, WorkflowVersion,
)
from app.utils.auth import generate_invitation_token
from app.utils.workflow_graph import empty_definition, validate_definition

#: Roles allowed to create a workflow or change its draft (mirrors the API).
AUTHOR_ROLES = (
    OrganizationRole.OWNER,
    OrganizationRole.ADMIN,
    OrganizationRole.EDITOR,
)


@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema object
    func: Callable[[Session, User, UUID, Dict[str, Any]], Dict[str, Any]]
    requires_confirmation: bool = False
    # Optional pre-flight check run when a confirmation tool is proposed:
    # raises PermissionError/ValueError to reject the proposal before an
    # AgentPendingAction row is created. State checks that can change by
    # approval time stay in `func`.
    authorize: Optional[Callable[[Session, User, UUID, Dict[str, Any]], None]] = None

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


def _require_author(db: Session, user: User, org_id: UUID) -> OrganizationMember:
    """Owner, admin or editor: the roles the workflow API lets write."""
    member = _require_member(db, user, org_id)
    if member.role not in AUTHOR_ROLES:
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


def _parse_definition(raw: Optional[str]) -> Dict[str, Any]:
    """A version's stored graph, tolerating a row written by an older build."""
    try:
        parsed = json.loads(raw or "{}")
    except (TypeError, ValueError):
        return {"nodes": [], "edges": []}
    return parsed if isinstance(parsed, dict) else {"nodes": [], "edges": []}


def _workflow_summary(workflow: Workflow) -> Dict[str, Any]:
    """The fields a reader needs without shipping the whole graph."""
    draft = workflow.draft()
    published = workflow.published()
    definition = _parse_definition(draft.definition if draft else None)
    return {
        "id": str(workflow.id),
        "name": workflow.name,
        "slug": workflow.slug,
        "description": workflow.description,
        "draft_version": draft.version if draft else None,
        "published_version": published.version if published else None,
        "node_count": len(definition.get("nodes") or []),
        "edge_count": len(definition.get("edges") or []),
        "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else None,
    }


def list_workflows(db: Session, user: User, org_id: UUID, args: Dict[str, Any]) -> Dict[str, Any]:
    """List workflows in the current organization, newest first."""
    _require_member(db, user, org_id)
    org = _org_or_404(db, org_id)

    query = db.query(Workflow).filter(Workflow.organization_id == org_id)
    needle = (args.get("query") or "").strip().lower()
    workflows = query.order_by(Workflow.created_at.desc()).all()
    if needle:
        workflows = [
            w for w in workflows
            if needle in w.name.lower() or needle in w.slug.lower()
        ]
    return {
        "organization": {"id": str(org.id), "name": org.name, "slug": org.slug},
        "workflows": [_workflow_summary(w) for w in workflows],
    }


def _select_workflow(db: Session, org_id: UUID, args: Dict[str, Any]) -> Workflow:
    """Look a workflow up by id or slug, scoped to one organization."""
    raw_id = args.get("workflow_id")
    slug = (args.get("slug") or "").strip()
    if bool(raw_id) == bool(slug):
        raise ValueError("Provide either workflow_id or slug, not both")

    query = db.query(Workflow).filter(Workflow.organization_id == org_id)
    if slug:
        workflow = query.filter(Workflow.slug == slug).first()
    else:
        try:
            workflow_id = UUID(str(raw_id))
        except (TypeError, ValueError):
            raise ValueError("workflow_id must be a UUID")
        workflow = query.filter(Workflow.id == workflow_id).first()
    if workflow is None:
        # Same answer for "does not exist" and "belongs to another org" —
        # the agent must not be able to probe for workflows it cannot see.
        raise LookupError("Workflow not found")
    return workflow


def get_workflow(db: Session, user: User, org_id: UUID, args: Dict[str, Any]) -> Dict[str, Any]:
    """Read one workflow (by id or slug) with its current draft graph."""
    _require_member(db, user, org_id)
    _org_or_404(db, org_id)

    workflow = _select_workflow(db, org_id, args)
    draft = workflow.draft()
    return {
        **_workflow_summary(workflow),
        "definition": _parse_definition(draft.definition if draft else None),
    }


def _validate_create_args(args: Dict[str, Any]) -> Tuple[str, Optional[str], Dict[str, Any]]:
    """Shared validation for create_workflow (proposal + execution)."""
    name = (args.get("name") or "").strip()
    if not name:
        raise ValueError("A workflow name is required")
    if len(name) > 255:
        raise ValueError("Workflow name must be 255 characters or fewer")
    description = args.get("description")
    if description is not None and not str(description).strip():
        description = None
    definition = args.get("definition")
    if definition is None:
        # A bare workflow starts with the API's empty draft, which has no
        # trigger node yet; only a graph the agent supplied must be coherent.
        definition = empty_definition()
    else:
        problems = validate_definition(definition)
        if problems:
            raise ValueError("Invalid workflow graph: " + "; ".join(problems))
    return name, (None if description is None else str(description)), definition


def _validate_draft_args(args: Dict[str, Any]) -> Dict[str, Any]:
    """Shared validation for replace_workflow_draft (proposal + execution)."""
    definition = args.get("definition")
    if definition is None:
        raise ValueError("A definition with nodes and edges is required")
    problems = validate_definition(definition)
    if problems:
        raise ValueError("Invalid workflow graph: " + "; ".join(problems))
    return definition


def authorize_create_workflow(db: Session, user: User, org_id: UUID, args: Dict[str, Any]) -> None:
    """Proposal-time check: authors only, with a valid name and graph."""
    _require_author(db, user, org_id)
    _org_or_404(db, org_id)
    _validate_create_args(args)


def create_workflow(db: Session, user: User, org_id: UUID, args: Dict[str, Any]) -> Dict[str, Any]:
    """Create a workflow with a draft at version 1. Requires human
    confirmation — runs only from the approve endpoint, never in-loop."""
    _require_author(db, user, org_id)
    org = _org_or_404(db, org_id)
    name, description, definition = _validate_create_args(args)

    # The slug is derived at execution time, so a name that gained a
    # sibling while the proposal waited still gets a unique slug.
    slug = _unique_slug(db, org_id, generate_slug(name))
    workflow = Workflow(
        organization_id=org_id,
        name=name,
        slug=slug,
        description=description,
        created_by=user.id,
    )
    db.add(workflow)
    db.flush()

    draft = WorkflowVersion(
        workflow_id=workflow.id,
        version=1,
        status="draft",
        definition=json.dumps(definition),
        created_by=user.id,
    )
    db.add(draft)
    db.commit()
    db.refresh(workflow)
    return {
        **_workflow_summary(workflow),
        "definition": _parse_definition(draft.definition),
        "organization": {"id": str(org.id), "name": org.name, "slug": org.slug},
    }


def authorize_replace_draft(db: Session, user: User, org_id: UUID, args: Dict[str, Any]) -> None:
    """Proposal-time check: authors only, on a workflow this org can see."""
    _require_author(db, user, org_id)
    _org_or_404(db, org_id)
    _select_workflow(db, org_id, args)
    _validate_draft_args(args)


def replace_workflow_draft(db: Session, user: User, org_id: UUID, args: Dict[str, Any]) -> Dict[str, Any]:
    """Replace a workflow's editable draft graph. Requires human
    confirmation — runs only from the approve endpoint, never in-loop.

    Published versions are never touched: this writes the draft row only,
    and opens one if the workflow somehow has none."""
    _require_author(db, user, org_id)
    _org_or_404(db, org_id)
    workflow = _select_workflow(db, org_id, args)
    definition = _validate_draft_args(args)

    draft = workflow.draft()
    if draft is None:
        draft = WorkflowVersion(
            workflow_id=workflow.id,
            version=max((v.version for v in workflow.versions), default=0) + 1,
            status="draft",
            definition=json.dumps(definition),
            created_by=user.id,
        )
        db.add(draft)
    else:
        draft.definition = json.dumps(definition)
    workflow.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(workflow)
    return {
        **_workflow_summary(workflow),
        "definition": definition,
    }


def _validate_invite_args(args: Dict[str, Any]) -> Tuple[str, OrganizationRole]:
    """Shared argument validation for invite_org_member (proposal + execute)."""
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
    return email, role


def authorize_invite_member(db: Session, user: User, org_id: UUID, args: Dict[str, Any]) -> None:
    """Proposal-time check: only admins may even propose an invite."""
    _require_admin(db, user, org_id)
    _validate_invite_args(args)


def invite_org_member(db: Session, user: User, org_id: UUID, args: Dict[str, Any]) -> Dict[str, Any]:
    """Create an organization invitation. Requires admin/owner and human
    confirmation — runs only from the approve endpoint, never in-loop."""
    _require_admin(db, user, org_id)
    _org_or_404(db, org_id)

    email, role = _validate_invite_args(args)

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
    name="list_workflows",
    description="List the workflows defined in the current organization, newest "
                "first, with their draft and published version numbers. Use "
                "`query` to narrow by name or slug.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Optional case-insensitive text to match against name or slug",
            },
        },
        "required": [],
    },
    func=list_workflows,
))

register(Tool(
    name="get_workflow",
    description="Read one workflow from the current organization — metadata plus "
                "the nodes and edges of its current draft. Look it up by id or "
                "by slug.",
    parameters={
        "type": "object",
        "properties": {
            "workflow_id": {
                "type": "string",
                "description": "Workflow UUID (use this or slug)",
            },
            "slug": {
                "type": "string",
                "description": "Workflow slug within the organization (use this or workflow_id)",
            },
        },
        "required": [],
    },
    func=get_workflow,
))

register(Tool(
    name="create_workflow",
    description="Create a workflow in the current organization with a draft at "
                "version 1, optionally seeded with a node/edge graph. "
                "REQUIRES HUMAN CONFIRMATION: the call only creates a pending "
                "action; a user must approve it before anything is written. "
                "Requires owner, admin or editor role.",
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Workflow name (the slug is derived from it)",
            },
            "description": {
                "type": "string",
                "description": "Optional short description",
            },
            "definition": {
                "type": "object",
                "description": "Optional graph: {\"nodes\": [...], \"edges\": [...]}",
            },
        },
        "required": ["name"],
    },
    func=create_workflow,
    requires_confirmation=True,
    authorize=authorize_create_workflow,
))

register(Tool(
    name="replace_workflow_draft",
    description="Replace the editable draft graph of an existing workflow. "
                "Published versions are never modified. REQUIRES HUMAN "
                "CONFIRMATION: the call only creates a pending action; a user "
                "must approve it before anything is written. Requires owner, "
                "admin or editor role.",
    parameters={
        "type": "object",
        "properties": {
            "workflow_id": {
                "type": "string",
                "description": "Workflow UUID (use this or slug)",
            },
            "slug": {
                "type": "string",
                "description": "Workflow slug within the organization (use this or workflow_id)",
            },
            "definition": {
                "type": "object",
                "description": "The new graph: {\"nodes\": [...], \"edges\": [...]}",
            },
        },
        "required": ["definition"],
    },
    func=replace_workflow_draft,
    requires_confirmation=True,
    authorize=authorize_replace_draft,
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
    authorize=authorize_invite_member,
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
        if tool.authorize is not None:
            try:
                tool.authorize(db, user, org_id, arguments or {})
            except (PermissionError, LookupError, ValueError) as exc:
                return {"ok": False, "error": str(exc)}
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
