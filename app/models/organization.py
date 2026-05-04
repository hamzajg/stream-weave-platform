import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from app.database import Base
from app.models.user import UUID


class OrganizationIndustry(PyEnum):
    MANUFACTURING = "manufacturing"
    FINANCE = "finance"
    INSURANCE = "insurance"
    HEALTHCARE = "healthcare"
    ECOMMERCE = "ecommerce"
    TRANSPORTATION = "transportation"
    AGRICULTURE = "agriculture"
    OTHER = "other"


class OrganizationSize(PyEnum):
    SIZE_1_10 = "1-10"
    SIZE_11_50 = "11-50"
    SIZE_51_200 = "51-200"
    SIZE_201_500 = "201-500"
    SIZE_500_PLUS = "500+"


class OrganizationRole(PyEnum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class Organization(Base):
    """Organization/tenant model for multi-tenancy."""
    __tablename__ = "organizations"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    industry = Column(Enum(OrganizationIndustry), nullable=False)
    size = Column(Enum(OrganizationSize), nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(UUID, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<Organization {self.name}>"


class OrganizationMember(Base):
    """Association model for organization membership."""
    __tablename__ = "organization_members"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(Enum(OrganizationRole), default=OrganizationRole.VIEWER, nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="members")
    user = relationship("User")

    def __repr__(self):
        return f"<OrganizationMember {self.user_id}@{self.organization_id} ({self.role})>"
