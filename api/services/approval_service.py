"""
Approval service — chain construction, step processing.

Thresholds (cents):
  < 5,000,000 (< INR 50k)  → Department Manager only
  5,000,000 - 19,999,999    → + Finance Head
  >= 20,000,000 (>= INR 200k) → + Finance Head + CFO
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status as http_status
import structlog

from api.models.approval import Approval
from api.models.department import Department
from api.models.user import User

logger = structlog.get_logger()

# Threshold boundaries in cents
THRESHOLD_FINANCE_HEAD = 5_000_000    # >= 5M cents needs finance_head
THRESHOLD_CFO = 20_000_000            # >= 20M cents needs CFO


@dataclass
class ApprovalStep:
    role: str
    user_id: str
    email: str
    approval_level: int


@dataclass
class ApprovalResult:
    is_final: bool
    is_rejected: bool
    next_approval: Optional[Approval] = None


async def get_department_manager(
    session: AsyncSession, department_id: str
) -> Optional[User]:
    """Look up department → manager_id → User."""
    dept_result = await session.execute(
        select(Department).where(Department.id == department_id)
    )
    dept = dept_result.scalar_one_or_none()
    if not dept or not dept.manager_id:
        return None

    user_result = await session.execute(
        select(User).where(User.id == dept.manager_id, User.is_active == True)  # noqa: E712
    )
    return user_result.scalar_one_or_none()


async def get_role_user(
    session: AsyncSession, tenant_id: str, role: str
) -> Optional[User]:
    """Find first active user with given role in tenant."""
    result = await session.execute(
        select(User).where(
            User.tenant_id == tenant_id,
            User.role == role,
            User.is_active == True,  # noqa: E712
        )
    )
    return result.scalars().first()


async def get_approval_chain(
    session: AsyncSession,
    tenant_id: str,
    entity_type: str,
    amount_cents: int,
    department_id: str,
) -> list[ApprovalStep]:
    """Build ordered approval chain based on amount thresholds."""
    chain: list[ApprovalStep] = []
    level = 1

    # Level 1: Department Manager (always required)
    manager = await get_department_manager(session, department_id)
    if not manager:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No active manager found for department",
        )
    chain.append(ApprovalStep(
        role="manager",
        user_id=str(manager.id),
        email=manager.email,
        approval_level=level,
    ))
    level += 1

    # Level 2: Finance Head (if amount >= 5M cents)
    if amount_cents >= THRESHOLD_FINANCE_HEAD:
        finance_head = await get_role_user(session, tenant_id, "finance_head")
        if not finance_head:
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No active finance_head user found in tenant",
            )
        chain.append(ApprovalStep(
            role="finance_head",
            user_id=str(finance_head.id),
            email=finance_head.email,
            approval_level=level,
        ))
        level += 1

    # Level 3: CFO (if amount >= 20M cents)
    if amount_cents >= THRESHOLD_CFO:
        cfo = await get_role_user(session, tenant_id, "cfo")
        if not cfo:
            raise HTTPException(
                status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No active CFO user found in tenant",
            )
        chain.append(ApprovalStep(
            role="cfo",
            user_id=str(cfo.id),
            email=cfo.email,
            approval_level=level,
        ))

    return chain


async def create_approval_workflow(
    session: AsyncSession,
    entity_type: str,
    entity_id: str,
    tenant_id: str,
    amount_cents: int,
    department_id: str,
) -> list[Approval]:
    """Create Approval records for the entity. All start PENDING."""
    chain = await get_approval_chain(
        session, tenant_id, entity_type, amount_cents, department_id
    )

    approvals = []
    for step in chain:
        approval = Approval(
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            approver_id=step.user_id,
            approval_level=step.approval_level,
            status="PENDING",
        )
        session.add(approval)
        approvals.append(approval)

    await session.flush()

    logger.info(
        "approval_workflow_created",
        entity_type=entity_type,
        entity_id=entity_id,
        steps=len(approvals),
    )
    return approvals


async def process_approval(
    session: AsyncSession,
    entity_type: str,
    entity_id: str,
    approver_id: str,
    action: str,
    comment: Optional[str] = None,
) -> ApprovalResult:
    """
    Process approve/reject for current step.

    Returns ApprovalResult with is_final, is_rejected, next_approval.
    Raises 403 if approver_id doesn't match current step.
    Raises 404 if no pending approval found.
    """
    # Get all approvals for this entity, ordered by level
    result = await session.execute(
        select(Approval)
        .where(
            Approval.entity_type == entity_type,
            Approval.entity_id == entity_id,
        )
        .order_by(Approval.approval_level)
    )
    all_approvals = list(result.scalars().all())

    if not all_approvals:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="No approval workflow found for this entity",
        )

    # Current step = first PENDING approval (lowest level)
    current = None
    for a in all_approvals:
        if a.status == "PENDING":
            current = a
            break

    if not current:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="No pending approval step found",
        )

    # Verify approver matches
    if str(current.approver_id) != str(approver_id):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "APPROVAL_NOT_YOUR_TURN",
                    "message": "You are not the current approver for this step",
                }
            },
        )

    now = datetime.utcnow()

    if action == "reject":
        current.status = "REJECTED"
        current.comments = comment
        current.approved_at = now

        # Cancel remaining PENDING approvals
        for a in all_approvals:
            if a.status == "PENDING" and a.id != current.id:
                a.status = "CANCELLED"

        await session.flush()
        return ApprovalResult(is_final=False, is_rejected=True)

    # action == "approve"
    current.status = "APPROVED"
    current.comments = comment
    current.approved_at = now
    await session.flush()

    # Find next PENDING step
    next_approval = None
    for a in all_approvals:
        if a.status == "PENDING" and a.id != current.id:
            next_approval = a
            break

    if next_approval:
        return ApprovalResult(
            is_final=False, is_rejected=False, next_approval=next_approval
        )

    # No more pending → fully approved
    return ApprovalResult(is_final=True, is_rejected=False)
