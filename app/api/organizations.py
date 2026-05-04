import re
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID

from app.database import get_db
from app.models import User, Organization, OrganizationMember, Invitation, OrganizationRole, OrganizationIndustry, OrganizationSize
from app.schemas.organization import (
    OrganizationCreate, OrganizationUpdate, OrganizationResponse,
    OrganizationMemberResponse, InvitationCreate, InvitationResponse,
    AcceptInvitation, OrganizationListResponse, OrganizationRole as RoleEnum
)
from app.api.auth import get_current_active_user
from app.utils.auth import generate_invitation_token

router = APIRouter()


def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from organization name."""
    slug = re.sub(r'[^\w\s-]', '', name.lower())
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug[:50]


@router.get("", response_model=List[OrganizationListResponse])
def list_organizations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all organizations where the current user is a member.
    """
    # Query organizations with member role and count
    results = db.query(
        Organization,
        OrganizationMember.role,
        func.count(OrganizationMember.id).over(partition_by=Organization.id).label('member_count')
    ).join(
        OrganizationMember, Organization.id == OrganizationMember.organization_id
    ).filter(
        OrganizationMember.user_id == current_user.id
    ).all()
    
    organizations = []
    for org, role, member_count in results:
        org_data = OrganizationListResponse(
            id=org.id,
            name=org.name,
            slug=org.slug,
            industry=org.industry,
            role=role,
            member_count=member_count
        )
        organizations.append(org_data)
    
    return organizations


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    org_data: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new organization and set current user as owner.
    """
    # Generate unique slug
    base_slug = generate_slug(org_data.name)
    slug = base_slug
    counter = 1
    
    while db.query(Organization).filter(Organization.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    # Create organization
    new_org = Organization(
        name=org_data.name,
        slug=slug,
        industry=org_data.industry,
        size=org_data.size,
        description=org_data.description,
        created_by=current_user.id,
    )
    
    db.add(new_org)
    db.flush()  # Get the org ID
    
    # Add creator as owner
    member = OrganizationMember(
        organization_id=new_org.id,
        user_id=current_user.id,
        role=OrganizationRole.OWNER,
    )
    db.add(member)
    
    db.commit()
    db.refresh(new_org)
    
    # Add member count
    member_count = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == new_org.id
    ).count()
    
    return OrganizationResponse(
        **{c.name: getattr(new_org, c.name) for c in new_org.__table__.columns},
        member_count=member_count
    )


@router.get("/{org_id}", response_model=OrganizationResponse)
def get_organization(
    org_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get organization details by ID.
    """
    # Check membership
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_id == current_user.id
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization"
        )
    
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    member_count = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id
    ).count()
    
    return OrganizationResponse(
        **{c.name: getattr(org, c.name) for c in org.__table__.columns},
        member_count=member_count
    )


@router.put("/{org_id}", response_model=OrganizationResponse)
def update_organization(
    org_id: UUID,
    org_data: OrganizationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update organization details (Admin or Owner only).
    """
    # Check permissions
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role.in_([OrganizationRole.OWNER, OrganizationRole.ADMIN])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Update fields
    if org_data.name:
        org.name = org_data.name
    if org_data.description is not None:
        org.description = org_data.description
    
    db.commit()
    db.refresh(org)
    
    member_count = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id
    ).count()
    
    return OrganizationResponse(
        **{c.name: getattr(org, c.name) for c in org.__table__.columns},
        member_count=member_count
    )


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization(
    org_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete organization (Owner only).
    """
    # Check ownership
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role == OrganizationRole.OWNER
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owner can delete"
        )
    
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    db.delete(org)
    db.commit()
    
    return None


@router.get("/{org_id}/members", response_model=List[OrganizationMemberResponse])
def list_members(
    org_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all members of an organization.
    """
    # Check membership
    current_member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_id == current_user.id
    ).first()
    
    if not current_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization"
        )
    
    members = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id
    ).all()
    
    return [
        OrganizationMemberResponse(
            id=m.id,
            user_id=m.user_id,
            organization_id=m.organization_id,
            role=m.role,
            joined_at=m.joined_at,
            user={"email": m.user.email, "full_name": m.user.full_name} if m.user else None
        )
        for m in members
    ]


@router.post("/{org_id}/invite", response_model=InvitationResponse)
def invite_member(
    org_id: UUID,
    invitation_data: InvitationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Invite a new member to the organization (Admin or Owner only).
    """
    # Check permissions
    member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role.in_([OrganizationRole.OWNER, OrganizationRole.ADMIN])
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to invite members"
        )
    
    # Check if user already exists in org
    existing_user = db.query(User).filter(User.email == invitation_data.email).first()
    if existing_user:
        existing_member = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == existing_user.id
        ).first()
        if existing_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this organization"
            )
    
    # Check for pending invitation
    existing_invite = db.query(Invitation).filter(
        Invitation.email == invitation_data.email,
        Invitation.organization_id == org_id,
        Invitation.accepted_at.is_(None)
    ).first()
    
    if existing_invite and not existing_invite.is_expired():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pending invitation already exists"
        )
    
    # Create invitation
    invitation = Invitation(
        email=invitation_data.email,
        organization_id=org_id,
        role=invitation_data.role,
        token=generate_invitation_token(),
        invited_by=current_user.id,
    )
    
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    
    return invitation


@router.post("/invitations/accept", response_model=OrganizationMemberResponse)
def accept_invitation(
    accept_data: AcceptInvitation,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Accept an organization invitation.
    """
    invitation = db.query(Invitation).filter(Invitation.token == accept_data.token).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
    
    if invitation.is_expired():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired"
        )
    
    if invitation.is_accepted():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has already been accepted"
        )
    
    # Check if email matches current user
    if invitation.email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invitation is for a different email address"
        )
    
    # Check if already a member
    existing_member = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == invitation.organization_id,
        OrganizationMember.user_id == current_user.id
    ).first()
    
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already a member of this organization"
        )
    
    # Add member
    new_member = OrganizationMember(
        organization_id=invitation.organization_id,
        user_id=current_user.id,
        role=invitation.role,
    )
    db.add(new_member)
    
    # Mark invitation as accepted
    from datetime import datetime
    invitation.accepted_at = datetime.utcnow()
    
    db.commit()
    db.refresh(new_member)
    
    return OrganizationMemberResponse(
        id=new_member.id,
        user_id=new_member.user_id,
        organization_id=new_member.organization_id,
        role=new_member.role,
        joined_at=new_member.joined_at,
        user={"email": current_user.email, "full_name": current_user.full_name}
    )
