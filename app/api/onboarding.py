from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum

from app.database import get_db
from app.models import User, Organization, OrganizationMember, OrganizationRole, OrganizationIndustry, OrganizationSize
from app.api.auth import get_current_active_user
from app.api.organizations import create_organization, generate_slug

router = APIRouter()


class OnboardingStep(str, Enum):
    PERSONAL = "personal"
    ORGANIZATION = "organization"
    INVITE = "invite"
    COMPLETE = "complete"


class PersonalInfoStep(BaseModel):
    """Step 1: Personal information."""
    full_name: str = Field(..., min_length=2, max_length=255)
    role_title: Optional[str] = Field(None, max_length=100)


class OrganizationStep(BaseModel):
    """Step 2: Organization details."""
    name: str = Field(..., min_length=1, max_length=255)
    industry: OrganizationIndustry
    size: OrganizationSize
    description: Optional[str] = None


class InviteStep(BaseModel):
    """Step 3: Team invitations."""
    invites: list = []  # List of {email, role} - processed separately


class OnboardingStatus(BaseModel):
    """Response with current onboarding status."""
    is_complete: bool
    current_step: OnboardingStep
    organization_id: Optional[UUID] = None
    organization_name: Optional[str] = None


class OnboardingComplete(BaseModel):
    """Final onboarding submission."""
    personal: PersonalInfoStep
    organization: OrganizationStep
    invites: InviteStep = InviteStep()


# In-memory store for onboarding progress (use Redis/cache in production)
onboarding_store = {}


def get_onboarding_key(user_id: UUID) -> str:
    return f"onboarding:{user_id}"


@router.get("/status", response_model=OnboardingStatus)
def get_onboarding_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current onboarding status for the user.
    """
    # Check if user has any organizations
    member = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    
    if member:
        org = db.query(Organization).filter(Organization.id == member.organization_id).first()
        return OnboardingStatus(
            is_complete=True,
            current_step=OnboardingStep.COMPLETE,
            organization_id=org.id if org else None,
            organization_name=org.name if org else None,
        )
    
    # Check in-progress onboarding
    key = get_onboarding_key(current_user.id)
    progress = onboarding_store.get(key, {})
    
    if not progress:
        return OnboardingStatus(
            is_complete=False,
            current_step=OnboardingStep.PERSONAL,
        )
    
    # Determine current step
    if progress.get("organization"):
        current_step = OnboardingStep.INVITE
    elif progress.get("personal"):
        current_step = OnboardingStep.ORGANIZATION
    else:
        current_step = OnboardingStep.PERSONAL
    
    return OnboardingStatus(
        is_complete=False,
        current_step=current_step,
    )


@router.post("/personal")
def save_personal_step(
    data: PersonalInfoStep,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Save personal information step.
    """
    # Update user's full name if different
    if data.full_name != current_user.full_name:
        current_user.full_name = data.full_name
        db.commit()
    
    # Save progress
    key = get_onboarding_key(current_user.id)
    if key not in onboarding_store:
        onboarding_store[key] = {}
    
    onboarding_store[key]["personal"] = {
        "full_name": data.full_name,
        "role_title": data.role_title,
    }
    
    return {
        "success": True,
        "next_step": OnboardingStep.ORGANIZATION,
        "message": "Personal information saved",
    }


@router.post("/organization")
def save_organization_step(
    data: OrganizationStep,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Save organization details step.
    """
    # Check if user already has org
    existing = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already belongs to an organization"
        )
    
    # Save progress
    key = get_onboarding_key(current_user.id)
    if key not in onboarding_store:
        onboarding_store[key] = {}
    
    onboarding_store[key]["organization"] = data.dict()
    
    return {
        "success": True,
        "next_step": OnboardingStep.INVITE,
        "message": "Organization details saved",
    }


@router.post("/invite")
def save_invite_step(
    data: InviteStep,
    current_user: User = Depends(get_current_active_user)
):
    """
    Save team invitations step (invites sent after completion).
    """
    key = get_onboarding_key(current_user.id)
    if key not in onboarding_store:
        onboarding_store[key] = {}
    
    onboarding_store[key]["invites"] = [i.dict() for i in data.invites] if data.invites else []
    
    return {
        "success": True,
        "next_step": OnboardingStep.COMPLETE,
        "message": "Invitation preferences saved",
    }


@router.post("/complete", response_model=OnboardingStatus)
def complete_onboarding(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Complete onboarding by creating organization and processing invites.
    """
    # Check if already complete
    existing = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    
    if existing:
        org = db.query(Organization).filter(Organization.id == existing.organization_id).first()
        return OnboardingStatus(
            is_complete=True,
            current_step=OnboardingStep.COMPLETE,
            organization_id=org.id,
            organization_name=org.name,
        )
    
    # Get saved progress
    key = get_onboarding_key(current_user.id)
    progress = onboarding_store.get(key, {})
    
    if not progress or "organization" not in progress:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization details not provided. Complete the organization step first."
        )
    
    org_data = progress["organization"]
    
    # Generate unique slug
    from app.api.organizations import generate_slug
    base_slug = generate_slug(org_data["name"])
    slug = base_slug
    counter = 1
    
    while db.query(Organization).filter(Organization.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    # Create organization
    new_org = Organization(
        name=org_data["name"],
        slug=slug,
        industry=OrganizationIndustry(org_data["industry"]),
        size=OrganizationSize(org_data["size"]),
        description=org_data.get("description"),
        created_by=current_user.id,
    )
    
    db.add(new_org)
    db.flush()
    
    # Add creator as owner
    member = OrganizationMember(
        organization_id=new_org.id,
        user_id=current_user.id,
        role=OrganizationRole.OWNER,
    )
    db.add(member)
    
    # Process invites (saved for later processing)
    invites = progress.get("invites", [])
    
    db.commit()
    db.refresh(new_org)
    
    # Clear onboarding progress
    if key in onboarding_store:
        del onboarding_store[key]
    
    return OnboardingStatus(
        is_complete=True,
        current_step=OnboardingStep.COMPLETE,
        organization_id=new_org.id,
        organization_name=new_org.name,
    )


@router.post("/skip")
def skip_onboarding(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Skip onboarding (user can complete later).
    Note: This creates a personal organization automatically.
    """
    # Check if already has org
    existing = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    
    if existing:
        return {
            "success": True,
            "message": "Already part of an organization",
        }
    
    # Create personal organization
    org_name = f"{current_user.full_name}'s Workspace"
    from app.api.organizations import generate_slug
    slug = generate_slug(org_name)
    counter = 1
    
    while db.query(Organization).filter(Organization.slug == slug).first():
        slug = f"{generate_slug(org_name)}-{counter}"
        counter += 1
    
    new_org = Organization(
        name=org_name,
        slug=slug,
        industry=OrganizationSize.OTHER,
        size=OrganizationSize.SIZE_1_10,
        description="Personal workspace",
        created_by=current_user.id,
    )
    
    db.add(new_org)
    db.flush()
    
    member = OrganizationMember(
        organization_id=new_org.id,
        user_id=current_user.id,
        role=OrganizationRole.OWNER,
    )
    db.add(member)
    
    db.commit()
    
    # Clear progress
    key = get_onboarding_key(current_user.id)
    if key in onboarding_store:
        del onboarding_store[key]
    
    return {
        "success": True,
        "message": "Onboarding skipped, personal workspace created",
        "organization_id": str(new_org.id),
        "organization_name": new_org.name,
    }
