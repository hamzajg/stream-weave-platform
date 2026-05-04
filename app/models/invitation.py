import uuid
from datetime import datetime, timedelta
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.organization import OrganizationRole
from app.models.user import UUID


class Invitation(Base):
    """Invitation model for team member invites."""
    __tablename__ = "invitations"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, index=True)
    organization_id = Column(UUID, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    role = Column(Enum(OrganizationRole), default=OrganizationRole.VIEWER, nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    invited_by = Column(UUID, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=7))
    accepted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    organization = relationship("Organization")
    inviter = relationship("User", foreign_keys=[invited_by])

    def __repr__(self):
        return f"<Invitation {self.email} -> {self.organization_id}>"

    def is_expired(self):
        return datetime.utcnow() > self.expires_at

    def is_accepted(self):
        return self.accepted_at is not None
