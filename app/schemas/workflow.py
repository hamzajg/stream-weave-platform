"""Request/response schemas for the workflow definition API."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WorkflowNode(BaseModel):
    """One node in a workflow graph."""

    id: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., min_length=1, max_length=50)
    label: Optional[str] = Field(None, max_length=255)
    config: Optional[Dict[str, Any]] = None


class WorkflowEdge(BaseModel):
    """A directed connection between two nodes."""

    source: str = Field(..., min_length=1, max_length=100)
    target: str = Field(..., min_length=1, max_length=100)


class WorkflowDefinition(BaseModel):
    """The graph a workflow version holds."""

    nodes: List[WorkflowNode] = Field(default_factory=list)
    edges: List[WorkflowEdge] = Field(default_factory=list)


class WorkflowCreate(BaseModel):
    """Create a workflow; the caller must be an author in the organization."""

    organization_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class WorkflowUpdate(BaseModel):
    """Rename or re-describe a workflow (the graph is replaced via /draft)."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class WorkflowVersionResponse(BaseModel):
    """A numbered graph snapshot."""

    id: UUID
    version: int
    status: str
    definition: Dict[str, Any]
    created_at: Optional[datetime] = None
    published_at: Optional[datetime] = None


class WorkflowResponse(BaseModel):
    """A workflow plus its current draft and published version numbers."""

    id: UUID
    organization_id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    draft_version: Optional[int] = None
    published_version: Optional[int] = None
    definition: Dict[str, Any]
