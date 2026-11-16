"""Workflow definition API: tenant-scoped CRUD for workflow graphs.

Routes under `/api/workflows`. Every route resolves the workflow *within the
caller's organizations* first (404 for anything else) and only then checks the
caller's role (403), so an outsider can never probe for existing ids
(specs/workflow-definitions, D4).
"""

import json
import re
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_active_user
from app.database import get_db
from app.models import (
    OrganizationMember,
    OrganizationRole,
    User,
    Workflow,
    WorkflowVersion,
)
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowResponse,
    WorkflowUpdate,
    WorkflowVersionResponse,
)
from app.utils.workflow_graph import empty_definition

router = APIRouter()

#: Roles allowed to change a workflow's metadata or graph.
AUTHOR_ROLES = (
    OrganizationRole.OWNER,
    OrganizationRole.ADMIN,
    OrganizationRole.EDITOR,
)
#: Roles allowed to delete a workflow.
ADMIN_ROLES = (OrganizationRole.OWNER, OrganizationRole.ADMIN)


def generate_slug(name: str) -> str:
    """URL-friendly slug, matching the organization slug convention."""
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return slug[:50] or "workflow"


def _unique_slug(db: Session, organization_id: UUID, base: str) -> str:
    """Return `base` or `base-2`, `base-3`, … free within the organization."""
    candidate = base
    suffix = 2
    while (
        db.query(Workflow.id)
        .filter(
            Workflow.organization_id == organization_id,
            Workflow.slug == candidate,
        )
        .first()
        is not None
    ):
        candidate = f"{base[:46]}-{suffix}"
        suffix += 1
    return candidate


def _membership(db: Session, organization_id: UUID, user_id: UUID):
    return (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
        .first()
    )


def _require_org(db: Session, organization_id: UUID, user: User, roles):
    """Authorize the caller in an organization or raise 404/403."""
    member = _membership(db, organization_id, user.id)
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
        )
    if roles and member.role not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your role does not allow this action",
        )
    return member


def _load_workflow(db: Session, workflow_id: UUID, user: User) -> Workflow:
    """Fetch a workflow the caller can see, or 404 (never leak other tenants)."""
    workflow = (
        db.query(Workflow)
        .join(
            OrganizationMember,
            OrganizationMember.organization_id == Workflow.organization_id,
        )
        .filter(Workflow.id == workflow_id, OrganizationMember.user_id == user.id)
        .first()
    )
    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found"
        )
    return workflow


def _require_role(db: Session, workflow: Workflow, user: User, roles) -> None:
    member = _membership(db, workflow.organization_id, user.id)
    if member is None or member.role not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your role does not allow this action",
        )


def _parse_definition(raw: Optional[str]) -> dict:
    try:
        parsed = json.loads(raw or "{}")
    except (TypeError, ValueError):
        return empty_definition()
    return parsed if isinstance(parsed, dict) else empty_definition()


def serialize_workflow(workflow: Workflow) -> dict:
    """Shape a workflow for `WorkflowResponse` (definition comes from the draft)."""
    draft = workflow.draft()
    published = workflow.published()
    return {
        "id": workflow.id,
        "organization_id": workflow.organization_id,
        "name": workflow.name,
        "slug": workflow.slug,
        "description": workflow.description,
        "created_at": workflow.created_at,
        "updated_at": workflow.updated_at,
        "draft_version": draft.version if draft else None,
        "published_version": published.version if published else None,
        "definition": _parse_definition(draft.definition if draft else None),
    }


def serialize_version(version: WorkflowVersion) -> dict:
    return {
        "id": version.id,
        "version": version.version,
        "status": version.status,
        "definition": _parse_definition(version.definition),
        "created_at": version.created_at,
        "published_at": version.published_at,
    }


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
def create_workflow(
    payload: WorkflowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a workflow with an empty draft at version 1."""
    _require_org(db, payload.organization_id, current_user, AUTHOR_ROLES)

    slug = _unique_slug(db, payload.organization_id, generate_slug(payload.name))
    workflow = Workflow(
        organization_id=payload.organization_id,
        name=payload.name.strip(),
        slug=slug,
        description=payload.description,
        created_by=current_user.id,
    )
    db.add(workflow)
    db.flush()

    draft = WorkflowVersion(
        workflow_id=workflow.id,
        version=1,
        status="draft",
        definition=json.dumps(empty_definition()),
        created_by=current_user.id,
    )
    db.add(draft)
    db.commit()
    db.refresh(workflow)
    return serialize_workflow(workflow)


@router.get("", response_model=List[WorkflowResponse])
def list_workflows(
    organization_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List workflows in the caller's organizations, newest first."""
    if organization_id is not None:
        _require_org(db, organization_id, current_user, ())

    query = (
        db.query(Workflow)
        .join(
            OrganizationMember,
            OrganizationMember.organization_id == Workflow.organization_id,
        )
        .filter(OrganizationMember.user_id == current_user.id)
    )
    if organization_id is not None:
        query = query.filter(Workflow.organization_id == organization_id)
    workflows = query.order_by(Workflow.created_at.desc()).all()
    return [serialize_workflow(workflow) for workflow in workflows]


@router.get("/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(
    workflow_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Read one workflow's metadata and current draft graph."""
    return serialize_workflow(_load_workflow(db, workflow_id, current_user))


@router.patch("/{workflow_id}", response_model=WorkflowResponse)
def update_workflow(
    workflow_id: UUID,
    payload: WorkflowUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Rename or re-describe a workflow. The slug stays stable (D5)."""
    workflow = _load_workflow(db, workflow_id, current_user)
    _require_role(db, workflow, current_user, AUTHOR_ROLES)

    if payload.name is not None:
        workflow.name = payload.name.strip()
    if payload.description is not None:
        workflow.description = payload.description
    workflow.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(workflow)
    return serialize_workflow(workflow)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(
    workflow_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a workflow and every version it holds."""
    workflow = _load_workflow(db, workflow_id, current_user)
    _require_role(db, workflow, current_user, ADMIN_ROLES)
    db.delete(workflow)
    db.commit()
    return None
