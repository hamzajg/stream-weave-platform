"""Workflow definition models: tenant-scoped workflows and versioned graphs.

`Workflow` is the identity of the thing (name, slug, owner) and
`WorkflowVersion` holds numbered, insert-only graph snapshots. Publishing
flips a version row to `published` and opens the next `draft`; no UPDATE ever
touches a published row (see specs/workflow-definitions/SPEC.md, D1/D2).
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.user import UUID


class Workflow(Base):
    """A workflow definition owned by exactly one organization."""

    __tablename__ = "workflows"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_workflows_org_slug"),
    )

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    slug = Column(String(80), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_by = Column(
        UUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    versions = relationship(
        "WorkflowVersion",
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="WorkflowVersion.version",
    )

    def draft(self):
        """The single editable version, if one exists."""
        for version in self.versions:
            if version.status == "draft":
                return version
        return None

    def published(self):
        """The highest published version, if any."""
        published = [v for v in self.versions if v.status == "published"]
        return published[-1] if published else None

    def __repr__(self):
        return f"<Workflow {self.slug} org={self.organization_id}>"


class WorkflowVersion(Base):
    """An immutable-once-published graph snapshot of a workflow."""

    __tablename__ = "workflow_versions"
    __table_args__ = (
        UniqueConstraint("workflow_id", "version", name="uq_workflow_versions_number"),
    )

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    workflow_id = Column(
        UUID,
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="draft", index=True)
    definition = Column(Text, nullable=False)
    created_by = Column(
        UUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)

    workflow = relationship("Workflow", back_populates="versions")

    def __repr__(self):
        return f"<WorkflowVersion {self.workflow_id} v{self.version} {self.status}>"
