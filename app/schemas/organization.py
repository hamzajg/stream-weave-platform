from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum


class OrganizationIndustry(str, Enum):
    MANUFACTURING = "manufacturing"
    FINANCE = "finance"
    INSURANCE = "insurance"
    HEALTHCARE = "healthcare"
    ECOMMERCE = "ecommerce"
    TRANSPORTATION = "transportation"
    AGRICULTURE = "agriculture"
    OTHER = "other"


class OrganizationSize(str, Enum):
    SIZE_1_10 = "1-10"
    SIZE_11_50 = "11-50"
    SIZE_51_200 = "51-200"
    SIZE_201_500 = "201-500"
    SIZE_500_PLUS = "500+"


class OrganizationRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class OrganizationBase(BaseModel):
    """Base organization schema."""
    name: str = Field(..., min_length=1, max_length=255)
    industry: OrganizationIndustry
    size: OrganizationSize
    description: Optional[str] = None


class OrganizationCreate(OrganizationBase):
    """Schema for organization creation."""
    pass


class OrganizationUpdate(BaseModel):
    """Schema for organization update."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class OrganizationResponse(OrganizationBase):
    """Schema for organization response."""
    id: UUID
    slug: str
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    member_count: Optional[int] = None

    class Config:
        from_attributes = True


class OrganizationMemberBase(BaseModel):
    """Base organization member schema."""
    user_id: UUID
    role: OrganizationRole


class OrganizationMemberCreate(OrganizationMemberBase):
    """Schema for adding organization member."""
    pass


class OrganizationMemberResponse(OrganizationMemberBase):
    """Schema for organization member response."""
    id: UUID
    organization_id: UUID
    user: Optional[dict] = None  # Will include user details
    joined_at: datetime

    class Config:
        from_attributes = True


class InvitationCreate(BaseModel):
    """Schema for creating invitation."""
    email: str = Field(..., min_length=1, max_length=255)
    role: OrganizationRole = OrganizationRole.VIEWER


class InvitationResponse(BaseModel):
    """Schema for invitation response."""
    id: UUID
    email: str
    organization_id: UUID
    role: OrganizationRole
    token: str
    invited_by: UUID
    expires_at: datetime
    accepted_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class AcceptInvitation(BaseModel):
    """Schema for accepting invitation."""
    token: str


class OrganizationListResponse(BaseModel):
    """Schema for list of organizations with role."""
    id: UUID
    name: str
    slug: str
    industry: OrganizationIndustry
    role: OrganizationRole
    member_count: int
