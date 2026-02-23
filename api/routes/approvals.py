"""
Approvals API routes — list pending approvals for the current user,
approve or reject an approval step.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.middleware.auth import get_current_user
from api.middleware.authorization import check_self_approval
from api.middleware.tenant import get_db_with_tenant
from api.models.approval import Approval
from api.models.purchase_request import PurchaseRequest
from api.models.user import User
from api.schemas.common import PaginatedResponse, build_pagination
from api.services.approval_service import process_approval
from api.services.audit_service import create_audit_log
from pydantic import BaseModel
from typing import Optional

logger = structlog.get_logger()
router = APIRouter()


class ApprovalListResponse(BaseModel):
    id: str
    tenant_id: str
    entity_type: str
    entity_id: str
    approver_id: str
    approval_level: int
    status: str
    comments: Optional[str] = None
    approved_at: Optional[str] = None
    created_at: str
    # Enriched fields
    entity_number: Optional[str] = None
    requester_name: Optional[str] = None
    total_cents: Optional[int] = None
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class ApprovalActionBody(BaseModel):
    comments: Optional[str] = None


async def _enrich_approval(db: AsyncSession, a: Approval) -> dict:
    """Enrich a raw Approval with entity details."""
    data = {
        "id": str(a.id),
        "tenant_id": str(a.tenant_id),
        "entity_type": a.entity_type,
        "entity_id": str(a.entity_id),
        "approver_id": str(a.approver_id),
        "approval_level": a.approval_level,
        "status": a.status,
        "comments": a.comments,
        "approved_at": a.approved_at.isoformat() if a.approved_at else None,
        "created_at": a.created_at.isoformat() if a.created_at else "",
    }

    # Enrich with PR details
    if a.entity_type in ("PurchaseRequest", "PR"):
        pr_result = await db.execute(
            select(PurchaseRequest).where(PurchaseRequest.id == a.entity_id)
        )
        pr = pr_result.scalar_one_or_none()
        if pr:
            data["entity_number"] = pr.pr_number
            data["total_cents"] = pr.total_cents
            data["description"] = pr.description
            # Get requester name
            user_result = await db.execute(
                select(User).where(User.id == pr.requester_id)
            )
            user = user_result.scalar_one_or_none()
            if user:
                data["requester_name"] = f"{user.first_name} {user.last_name}"

    return data


@router.get("", response_model=PaginatedResponse[ApprovalListResponse])
async def list_approvals(
    status_filter: str = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    """List approvals assigned to the current user."""
    q = select(Approval).where(Approval.approver_id == current_user["user_id"])
    count_q = select(func.count(Approval.id)).where(
        Approval.approver_id == current_user["user_id"]
    )

    if status_filter:
        q = q.where(Approval.status == status_filter)
        count_q = count_q.where(Approval.status == status_filter)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        q.order_by(Approval.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    raw_approvals = result.scalars().all()

    items = []
    for a in raw_approvals:
        enriched = await _enrich_approval(db, a)
        items.append(ApprovalListResponse(**enriched))

    return PaginatedResponse(
        data=items, pagination=build_pagination(page, limit, total)
    )


@router.post("/{approval_id}/approve", response_model=ApprovalListResponse)
async def approve_step(
    approval_id: str,
    body: ApprovalActionBody = ApprovalActionBody(),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    """Approve the current step."""
    # Get the approval first
    result = await db.execute(select(Approval).where(Approval.id == approval_id))
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    # Self-approval guard: prevent approving your own PR
    if approval.entity_type in ("PurchaseRequest", "PR"):
        pr_result = await db.execute(
            select(PurchaseRequest).where(PurchaseRequest.id == approval.entity_id)
        )
        pr = pr_result.scalar_one_or_none()
        if pr:
            check_self_approval(current_user["user_id"], str(pr.requester_id))

    approval_result = await process_approval(
        db,
        approval.entity_type,
        str(approval.entity_id),
        current_user["user_id"],
        "approve",
        body.comments,
    )

    # If final approval and entity is PR → update PR status
    if approval_result.is_final and approval.entity_type in ("PurchaseRequest", "PR"):
        pr_result = await db.execute(
            select(PurchaseRequest).where(PurchaseRequest.id == approval.entity_id)
        )
        pr = pr_result.scalar_one_or_none()
        if pr:
            from datetime import datetime
            pr.status = "APPROVED"
            pr.approved_at = datetime.utcnow()

    await create_audit_log(
        db,
        tenant_id=current_user["tenant_id"],
        actor_id=current_user["user_id"],
        action="APPROVAL_APPROVED",
        entity_type=approval.entity_type,
        entity_id=str(approval.entity_id),
        before_state={"status": "PENDING"},
        after_state={"status": "APPROVED"},
        actor_email=current_user.get("email"),
    )

    await db.flush()

    # Refresh and return
    await db.refresh(approval)
    enriched = await _enrich_approval(db, approval)
    return ApprovalListResponse(**enriched)


@router.post("/{approval_id}/reject", response_model=ApprovalListResponse)
async def reject_step(
    approval_id: str,
    body: ApprovalActionBody,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    """Reject the current step."""
    result = await db.execute(select(Approval).where(Approval.id == approval_id))
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    # Self-rejection guard: prevent rejecting your own PR
    if approval.entity_type in ("PurchaseRequest", "PR"):
        pr_result = await db.execute(
            select(PurchaseRequest).where(PurchaseRequest.id == approval.entity_id)
        )
        pr = pr_result.scalar_one_or_none()
        if pr:
            check_self_approval(current_user["user_id"], str(pr.requester_id))

    await process_approval(
        db,
        approval.entity_type,
        str(approval.entity_id),
        current_user["user_id"],
        "reject",
        body.comments,
    )

    # If entity is PR → update PR status to REJECTED
    if approval.entity_type in ("PurchaseRequest", "PR"):
        pr_result = await db.execute(
            select(PurchaseRequest).where(PurchaseRequest.id == approval.entity_id)
        )
        pr = pr_result.scalar_one_or_none()
        if pr:
            pr.status = "REJECTED"
            # Release budget reservation
            from api.services.budget_service import release_budget_reservation
            await release_budget_reservation(db, approval.entity_type, str(pr.id))

    await create_audit_log(
        db,
        tenant_id=current_user["tenant_id"],
        actor_id=current_user["user_id"],
        action="APPROVAL_REJECTED",
        entity_type=approval.entity_type,
        entity_id=str(approval.entity_id),
        before_state={"status": "PENDING"},
        after_state={"status": "REJECTED"},
        actor_email=current_user.get("email"),
    )

    await db.flush()

    await db.refresh(approval)
    enriched = await _enrich_approval(db, approval)
    return ApprovalListResponse(**enriched)
