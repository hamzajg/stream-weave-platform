from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from uuid import UUID
from pydantic import BaseModel
from enum import Enum

from app.database import get_db
from app.models import User, Organization, OrganizationMember, OrganizationRole
from app.api.auth import get_current_active_user

router = APIRouter()


class DashboardStats(BaseModel):
    """Dashboard statistics response."""
    total_workflows: int
    total_runs: int
    active_agents: int
    success_rate: float  # percentage
    runs_today: int
    runs_this_week: int


class RecentWorkflow(BaseModel):
    """Recent workflow item."""
    id: UUID
    name: str
    status: str  # active, paused, draft
    last_run_at: Optional[datetime]
    run_count: int
    created_at: datetime


class ActivityType(str, Enum):
    WORKFLOW_CREATED = "workflow_created"
    WORKFLOW_RUN = "workflow_run"
    WORKFLOW_UPDATED = "workflow_updated"
    MEMBER_INVITED = "member_invited"
    MEMBER_JOINED = "member_joined"
    AGENT_CREATED = "agent_created"


class ActivityItem(BaseModel):
    """Activity feed item."""
    id: UUID
    type: ActivityType
    description: str
    user: dict  # {id, full_name, email}
    entity_id: Optional[UUID]
    entity_name: Optional[str]
    created_at: datetime


class OrganizationSummary(BaseModel):
    """Organization summary for selector."""
    id: UUID
    name: str
    slug: str
    role: OrganizationRole
    member_count: int


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    org_id: Optional[UUID] = Query(None, description="Organization ID (defaults to user's active org)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get dashboard statistics for the organization.
    """
    # Determine organization
    if org_id:
        # Verify membership
        member = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Not a member of this organization")
    else:
        # Use first org
        member = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == current_user.id
        ).first()
        if not member:
            raise HTTPException(status_code=404, detail="No organization found. Complete onboarding first.")
        org_id = member.organization_id
    
    # For iteration 2, return placeholder stats
    # In iteration 3, these will be calculated from Workflow and WorkflowRun tables
    return DashboardStats(
        total_workflows=0,
        total_runs=0,
        active_agents=0,
        success_rate=0.0,
        runs_today=0,
        runs_this_week=0,
    )


@router.get("/recent-workflows", response_model=List[RecentWorkflow])
def get_recent_workflows(
    org_id: Optional[UUID] = Query(None),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get recent workflows for the organization.
    """
    # Determine organization
    if org_id:
        member = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Not a member of this organization")
    else:
        member = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == current_user.id
        ).first()
        if not member:
            return []
        org_id = member.organization_id
    
    # Placeholder - will return actual workflows in iteration 3
    return []


@router.get("/activity", response_model=List[ActivityItem])
def get_activity_feed(
    org_id: Optional[UUID] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get activity feed for the organization.
    """
    # Determine organization
    if org_id:
        member = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Not a member of this organization")
    else:
        member = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == current_user.id
        ).first()
        if not member:
            return []
        org_id = member.organization_id
    
    # Placeholder - will return actual activity in iteration 3
    # For now, show recent member joins
    recent_members = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id
    ).order_by(desc(OrganizationMember.joined_at)).limit(limit).all()
    
    activity = []
    for member in recent_members:
        if member.user:
            activity.append(ActivityItem(
                id=member.id,
                type=ActivityType.MEMBER_JOINED,
                description=f"{member.user.full_name} joined the organization",
                user={
                    "id": str(member.user.id),
                    "full_name": member.user.full_name,
                    "email": member.user.email,
                },
                entity_id=member.user_id,
                entity_name=member.user.full_name,
                created_at=member.joined_at,
            ))
    
    return activity


@router.get("/organizations", response_model=List[OrganizationSummary])
def get_user_organizations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get list of organizations for the current user with dashboard summary.
    """
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
        organizations.append(OrganizationSummary(
            id=org.id,
            name=org.name,
            slug=org.slug,
            role=role,
            member_count=member_count,
        ))
    
    return organizations


@router.post("/quick-action/create-workflow")
def quick_create_workflow(
    name: str,
    org_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Quick action: Create a new workflow (placeholder for iteration 3).
    """
    # Determine organization
    if org_id:
        member = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Not a member of this organization")
    else:
        member = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == current_user.id
        ).first()
        if not member:
            raise HTTPException(status_code=404, detail="No organization found")
        org_id = member.organization_id
    
    # Placeholder - will create actual workflow in iteration 3
    return {
        "success": True,
        "message": "Workflow creation will be available in Iteration 3",
        "placeholder_id": "00000000-0000-0000-0000-000000000000",
    }


@router.post("/quick-action/invite-team")
def quick_invite_team(
    emails: List[str],
    org_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Quick action: Invite team members (delegates to organizations API).
    """
    from app.api.organizations import invite_member
    from app.schemas.organization import InvitationCreate, OrganizationRole
    
    # Determine organization
    if org_id:
        member = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Not a member of this organization")
    else:
        member = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == current_user.id
        ).first()
        if not member:
            raise HTTPException(status_code=404, detail="No organization found")
        org_id = member.organization_id
    
    # Check permissions
    if member.role not in [OrganizationRole.OWNER, OrganizationRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Insufficient permissions to invite members")
    
    invited = []
    failed = []
    
    for email in emails:
        try:
            invite_data = InvitationCreate(email=email, role=OrganizationRole.VIEWER)
            result = invite_member(org_id, invite_data, db, current_user)
            invited.append({"email": email, "id": str(result.id)})
        except Exception as e:
            failed.append({"email": email, "error": str(e)})
    
    return {
        "success": len(failed) == 0,
        "invited": invited,
        "failed": failed,
    }
