from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.middleware.auth import get_current_user
from api.middleware.tenant import get_db_with_tenant
from api.middleware.authorization import require_roles, check_self_approval
from api.models.purchase_request import PurchaseRequest, PrLineItem
from api.models.approval import Approval
from api.models.user import User
from api.schemas.purchase_request import (
    PurchaseRequestCreate,
    PurchaseRequestUpdate,
    PurchaseRequestResponse,
    PrLineItemResponse,
    ApproveRejectRequest,
    RejectRequest,
    RetractRequest,
)
from api.schemas.common import PaginatedResponse, build_pagination
from api.services.budget_service import (
    get_current_fiscal_period,
    check_budget_availability,
    reserve_budget,
    release_budget_reservation,
)
from api.services.approval_service import create_approval_workflow, process_approval
from api.services.audit_service import create_audit_log
from api.services.notification_service import send_notification

logger = structlog.get_logger()
router = APIRouter()

PR_PREFIX = "PR"


async def _generate_pr_number(db: AsyncSession) -> str:
    result = await db.execute(select(func.count(PurchaseRequest.id)))
    count = (result.scalar() or 0) + 1
    return f"{PR_PREFIX}-{count:06d}"


def _line_to_response(li: PrLineItem) -> PrLineItemResponse:
    return PrLineItemResponse(
        id=str(li.id),
        line_number=li.line_number,
        description=li.description,
        quantity=li.quantity,
        unit_price_cents=li.unit_price_cents,
        category=li.category,
        notes=li.notes,
    )


def _to_response(pr: PurchaseRequest, line_items: list[PrLineItem]) -> PurchaseRequestResponse:
    return PurchaseRequestResponse(
        id=str(pr.id),
        tenant_id=str(pr.tenant_id),
        pr_number=pr.pr_number,
        requester_id=str(pr.requester_id),
        department_id=str(pr.department_id),
        status=pr.status,
        total_cents=pr.total_cents,
        currency=pr.currency,
        description=pr.description,
        justification=pr.justification,
        line_items=[_line_to_response(li) for li in line_items],
        created_at=pr.created_at.isoformat() if pr.created_at else "",
        updated_at=pr.updated_at.isoformat() if pr.updated_at else "",
        submitted_at=pr.submitted_at.isoformat() if pr.submitted_at else None,
        approved_at=pr.approved_at.isoformat() if pr.approved_at else None,
    )


async def _get_line_items(db: AsyncSession, pr_id) -> list[PrLineItem]:
    result = await db.execute(
        select(PrLineItem).where(PrLineItem.pr_id == pr_id).order_by(PrLineItem.line_number)
    )
    return list(result.scalars().all())


# ---------- LIST / GET ----------


@router.get("", response_model=PaginatedResponse[PurchaseRequestResponse])
async def list_purchase_requests(
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=50),
    pr_status: str = Query(None, alias="status"),
    department_id: str = Query(None),
    requester_id: str = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    logger.info("pr_list_request", page=page, status=pr_status, dept=department_id, req=requester_id)

    q = select(PurchaseRequest).where(PurchaseRequest.deleted_at == None)  # noqa: E711
    count_q = select(func.count(PurchaseRequest.id)).where(PurchaseRequest.deleted_at == None)  # noqa: E711

    if pr_status:
        q = q.where(PurchaseRequest.status == pr_status)
        count_q = count_q.where(PurchaseRequest.status == pr_status)

    if department_id:
        q = q.where(PurchaseRequest.department_id == department_id)
        count_q = count_q.where(PurchaseRequest.department_id == department_id)
    
    # ---------------------------------------------------------
    # VISIBILITY LOGIC
    # ---------------------------------------------------------
    
    # Roles that can see ALL PRs (across departments)
    privileged_roles = ["admin", "manager", "finance_head", "cfo", "procurement", "viewer"]
    
    user_role = current_user["role"]
    user_dept = current_user.get("department_id")

    if user_role in privileged_roles:
        pass  # No extra filter needed (except Drafts below)

    elif user_role == "manager" and user_dept:
        # Managers see their department + their own
        q = q.where(
            or_(
                PurchaseRequest.department_id == user_dept,
                PurchaseRequest.requester_id == current_user["user_id"]
            )
        )
        count_q = count_q.where(
            or_(
                PurchaseRequest.department_id == user_dept,
                PurchaseRequest.requester_id == current_user["user_id"]
            )
        )

    else:
        # Everyone else (Employee, Vendor, etc.) -> OWN ONLY
        q = q.where(PurchaseRequest.requester_id == current_user["user_id"])
        count_q = count_q.where(PurchaseRequest.requester_id == current_user["user_id"])

    # ---------------------------------------------------------
    # DRAFT PRIVACY
    # ---------------------------------------------------------
    # Drafts are private to the requester, regardless of role
    # (unless you are the requester)
    # ---------------------------------------------------------
    q = q.where(
        or_(
            PurchaseRequest.status != "DRAFT",
            PurchaseRequest.requester_id == current_user["user_id"]
        )
    )
    count_q = count_q.where(
        or_(
            PurchaseRequest.status != "DRAFT",
            PurchaseRequest.requester_id == current_user["user_id"]
        )
    )

    if requester_id:
        q = q.where(PurchaseRequest.requester_id == requester_id)
        count_q = count_q.where(PurchaseRequest.requester_id == requester_id)

    # Manager: restrict to own department (REMOVED - handled above)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        q.order_by(PurchaseRequest.created_at.desc()).offset((page - 1) * limit).limit(limit)
    )
    prs = result.scalars().all()
    logger.info("pr_list_result", count=len(prs), total=total)

    # Batch load all line items in a single query to avoid N+1
    pr_ids = [pr.id for pr in prs]
    if pr_ids:
        li_result = await db.execute(
            select(PrLineItem)
            .where(PrLineItem.pr_id.in_(pr_ids))
            .order_by(PrLineItem.pr_id, PrLineItem.line_number)
        )
        all_line_items = li_result.scalars().all()
        li_map: dict = {}
        for li in all_line_items:
            li_map.setdefault(str(li.pr_id), []).append(li)
    else:
        li_map = {}

    items = []
    for pr in prs:
        items.append(_to_response(pr, li_map.get(str(pr.id), [])))

    return PaginatedResponse(data=items, pagination=build_pagination(page, limit, total))


@router.get("/{pr_id}", response_model=PurchaseRequestResponse)
async def get_purchase_request(
    pr_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(
        select(PurchaseRequest).where(
            PurchaseRequest.id == pr_id, PurchaseRequest.deleted_at == None  # noqa: E711
        )
    )
    pr = result.scalar_one_or_none()
    if not pr:
        raise HTTPException(status_code=404, detail="Purchase request not found")

    line_items = await _get_line_items(db, pr.id)
    return _to_response(pr, line_items)


# ---------- CREATE / UPDATE ----------


@router.post("", response_model=PurchaseRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase_request(
    body: PurchaseRequestCreate,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("procurement", "procurement_lead", "admin", "manager", "finance")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    total_cents = sum(li.quantity * li.unit_price_cents for li in body.line_items)

    pr_number = await _generate_pr_number(db)

    pr = PurchaseRequest(
        tenant_id=current_user["tenant_id"],
        pr_number=pr_number,
        requester_id=current_user["user_id"],
        department_id=body.department_id,
        status="DRAFT",
        total_cents=total_cents,
        currency="INR",
        description=body.description,
        justification=body.justification,
    )
    db.add(pr)
    await db.flush()

    for idx, li_data in enumerate(body.line_items, start=1):
        li = PrLineItem(
            pr_id=pr.id,
            line_number=idx,
            description=li_data.description,
            quantity=li_data.quantity,
            unit_price_cents=li_data.unit_price_cents,
            category=li_data.category,
            notes=li_data.notes,
        )
        db.add(li)

    await db.flush()
    line_items = await _get_line_items(db, pr.id)
    return _to_response(pr, line_items)


@router.put("/{pr_id}", response_model=PurchaseRequestResponse)
async def update_purchase_request(
    pr_id: str,
    body: PurchaseRequestUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(
        select(PurchaseRequest).where(
            PurchaseRequest.id == pr_id, PurchaseRequest.deleted_at == None  # noqa: E711
        )
    )
    pr = result.scalar_one_or_none()
    if not pr:
        raise HTTPException(status_code=404, detail="Purchase request not found")

    if pr.status != "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only update purchase requests in DRAFT status",
        )

    if str(pr.requester_id) != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the requester can update this purchase request",
        )

    if body.description is not None:
        pr.description = body.description
    if body.justification is not None:
        pr.justification = body.justification

    if body.line_items is not None:
        existing = await db.execute(select(PrLineItem).where(PrLineItem.pr_id == pr.id))
        for li in existing.scalars().all():
            await db.delete(li)

        total_cents = 0
        for idx, li_data in enumerate(body.line_items, start=1):
            li = PrLineItem(
                pr_id=pr.id,
                line_number=idx,
                description=li_data.description,
                quantity=li_data.quantity,
                unit_price_cents=li_data.unit_price_cents,
                category=li_data.category,
                notes=li_data.notes,
            )
            db.add(li)
            total_cents += li_data.quantity * li_data.unit_price_cents
        pr.total_cents = total_cents

    await db.flush()
    line_items = await _get_line_items(db, pr.id)
    return _to_response(pr, line_items)


@router.delete("/{pr_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_purchase_request(
    pr_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(
        select(PurchaseRequest).where(
            PurchaseRequest.id == pr_id, PurchaseRequest.deleted_at == None  # noqa: E711
        )
    )
    pr = result.scalar_one_or_none()
    if not pr:
        raise HTTPException(status_code=404, detail="Purchase request not found")

    if pr.status != "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only delete purchase requests in DRAFT status",
        )

    if str(pr.requester_id) != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the requester can delete this purchase request",
        )

    before = {"status": pr.status, "deleted_at": None}
    pr.deleted_at = datetime.utcnow()
    after = {"status": pr.status, "deleted_at": pr.deleted_at.isoformat()}

    await create_audit_log(
        db,
        tenant_id=current_user["tenant_id"],
        actor_id=current_user["user_id"],
        action="PR_DELETED",
        entity_type="PR",
        entity_id=str(pr.id),
        before_state=before,
        after_state=after,
        actor_email=current_user.get("email"),
    )

    await db.flush()


# ---------- SUBMIT ----------


@router.post("/{pr_id}/submit", response_model=PurchaseRequestResponse)
async def submit_purchase_request(
    pr_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    logger.info("pr_submit_request", pr_id=pr_id, user=current_user["user_id"])
    result = await db.execute(
        select(PurchaseRequest).where(
            PurchaseRequest.id == pr_id, PurchaseRequest.deleted_at == None  # noqa: E711
        )
    )
    pr = result.scalar_one_or_none()
    if not pr:
        raise HTTPException(status_code=404, detail="Purchase request not found")

    if pr.status != "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only submit purchase requests in DRAFT status",
        )

    if str(pr.requester_id) != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the requester can submit this purchase request",
        )

    # Check has line items
    li_count = await db.execute(
        select(func.count(PrLineItem.id)).where(PrLineItem.pr_id == pr.id)
    )
    if (li_count.scalar() or 0) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot submit a purchase request with no line items",
        )

    # 1. Budget check + reserve (pessimistic lock)
    fy, q = get_current_fiscal_period()
    budget_check = await check_budget_availability(
        db, str(pr.department_id), pr.total_cents, fy, q
    )
    if not budget_check.success:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": budget_check.error_code,
                    "message": budget_check.message,
                    "available_cents": budget_check.available_cents,
                    "requested_cents": budget_check.requested_cents,
                }
            },
        )

    # 2. Reserve budget
    await reserve_budget(
        db,
        budget_check.budget_id,
        "PR",
        str(pr.id),
        pr.total_cents,
        current_user["tenant_id"],
    )

    # 3. Create approval workflow
    approvals = await create_approval_workflow(
        db,
        "PR",
        str(pr.id),
        current_user["tenant_id"],
        pr.total_cents,
        str(pr.department_id),
    )

    # 4. Transition to PENDING
    before = {"status": pr.status}
    pr.status = "PENDING"
    pr.submitted_at = datetime.utcnow()
    after = {"status": pr.status}

    # 5. Audit log
    await create_audit_log(
        db,
        tenant_id=current_user["tenant_id"],
        actor_id=current_user["user_id"],
        action="PR_SUBMITTED",
        entity_type="PR",
        entity_id=str(pr.id),
        before_state=before,
        after_state=after,
        actor_email=current_user.get("email"),
    )

    await db.flush()

    # 6. Notify first approver (resolve email while session open)
    first_approver = approvals[0]
    approver_result = await db.execute(
        select(User).where(User.id == first_approver.approver_id)
    )
    approver_user = approver_result.scalar_one_or_none()
    approver_email = approver_user.email if approver_user else None

    if approver_email:
        notification_ctx = {
            "pr_number": pr.pr_number,
            "description": pr.description or "",
            "currency": pr.currency,
            "amount_cents": pr.total_cents,
            "requester_email": current_user.get("email", ""),
        }
        background_tasks.add_task(
            send_notification,
            template_id="pr_approval_request",
            recipient_emails=[approver_email],
            context=notification_ctx,
        )

    line_items = await _get_line_items(db, pr.id)
    logger.info("pr_submitted", pr_id=str(pr.id), pr_number=pr.pr_number)
    return _to_response(pr, line_items)


@router.post("/{pr_id}/retract", response_model=PurchaseRequestResponse)
async def retract_purchase_request(
    pr_id: str,
    body: RetractRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(
        select(PurchaseRequest).where(
            PurchaseRequest.id == pr_id, PurchaseRequest.deleted_at == None  # noqa: E711
        )
    )
    pr = result.scalar_one_or_none()
    if not pr:
        raise HTTPException(status_code=404, detail="Purchase request not found")

    if pr.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only retract purchase requests in PENDING status",
        )

    if str(pr.requester_id) != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the requester can retract this purchase request",
        )

    # Release budget reservation for this PR.
    await release_budget_reservation(db, "PR", str(pr.id))

    # Cancel all pending approvals for this PR.
    approvals_result = await db.execute(
        select(Approval).where(
            Approval.entity_type == "PR",
            Approval.entity_id == pr.id,
            Approval.status == "PENDING",
        )
    )
    for approval in approvals_result.scalars().all():
        approval.status = "CANCELLED"
        if body.reason:
            approval.comments = f"Retracted by requester: {body.reason}"

    before = {"status": pr.status}
    pr.status = "CANCELLED"
    after = {"status": pr.status}

    await create_audit_log(
        db,
        tenant_id=current_user["tenant_id"],
        actor_id=current_user["user_id"],
        action="PR_RETRACTED",
        entity_type="PR",
        entity_id=str(pr.id),
        before_state=before,
        after_state=after,
        actor_email=current_user.get("email"),
    )

    await db.flush()
    line_items = await _get_line_items(db, pr.id)
    logger.info("pr_retracted", pr_id=str(pr.id), by=current_user["user_id"])
    return _to_response(pr, line_items)


# ---------- APPROVE ----------


@router.post("/{pr_id}/approve", response_model=PurchaseRequestResponse)
async def approve_purchase_request(
    pr_id: str,
    body: ApproveRejectRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("manager", "finance_head", "cfo", "admin")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(
        select(PurchaseRequest).where(
            PurchaseRequest.id == pr_id, PurchaseRequest.deleted_at == None  # noqa: E711
        )
    )
    pr = result.scalar_one_or_none()
    if not pr:
        raise HTTPException(status_code=404, detail="Purchase request not found")

    if pr.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only approve purchase requests in PENDING status",
        )

    # Prevent self-approval
    check_self_approval(current_user["user_id"], str(pr.requester_id))

    # Process approval step
    approval_result = await process_approval(
        db, "PR", str(pr.id), current_user["user_id"], "approve", body.comment
    )

    before = {"status": pr.status}

    if approval_result.is_final:
        # Fully approved
        pr.status = "APPROVED"
        pr.approved_at = datetime.utcnow()

        # Notify requester
        requester_result = await db.execute(
            select(User).where(User.id == pr.requester_id)
        )
        requester = requester_result.scalar_one_or_none()
        if requester:
            background_tasks.add_task(
                send_notification,
                template_id="pr_approved",
                recipient_emails=[requester.email],
                context={
                    "pr_number": pr.pr_number,
                    "currency": pr.currency,
                    "amount_cents": pr.total_cents,
                },
            )
    else:
        # Notify next approver
        next_app = approval_result.next_approval
        if next_app:
            next_user_result = await db.execute(
                select(User).where(User.id == next_app.approver_id)
            )
            next_user = next_user_result.scalar_one_or_none()
            if next_user:
                background_tasks.add_task(
                    send_notification,
                    template_id="pr_approval_request",
                    recipient_emails=[next_user.email],
                    context={
                        "pr_number": pr.pr_number,
                        "description": pr.description or "",
                        "currency": pr.currency,
                        "amount_cents": pr.total_cents,
                        "requester_email": "",
                    },
                )

    after = {"status": pr.status}

    # Audit log
    await create_audit_log(
        db,
        tenant_id=current_user["tenant_id"],
        actor_id=current_user["user_id"],
        action="PR_APPROVED" if approval_result.is_final else "PR_APPROVAL_STEP",
        entity_type="PR",
        entity_id=str(pr.id),
        before_state=before,
        after_state=after,
        actor_email=current_user.get("email"),
    )

    await db.flush()
    line_items = await _get_line_items(db, pr.id)
    logger.info(
        "pr_approval_processed",
        pr_id=str(pr.id),
        is_final=approval_result.is_final,
        approver=current_user["user_id"],
    )
    return _to_response(pr, line_items)


# ---------- REJECT ----------


@router.post("/{pr_id}/reject", response_model=PurchaseRequestResponse)
async def reject_purchase_request(
    pr_id: str,
    body: RejectRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("manager", "finance_head", "cfo", "admin")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(
        select(PurchaseRequest).where(
            PurchaseRequest.id == pr_id, PurchaseRequest.deleted_at == None  # noqa: E711
        )
    )
    pr = result.scalar_one_or_none()
    if not pr:
        raise HTTPException(status_code=404, detail="Purchase request not found")

    if pr.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only reject purchase requests in PENDING status",
        )

    # Process rejection
    await process_approval(
        db, "PR", str(pr.id), current_user["user_id"], "reject", body.reason
    )

    # Release budget reservation
    await release_budget_reservation(db, "PR", str(pr.id))

    before = {"status": pr.status}
    pr.status = "REJECTED"
    after = {"status": pr.status}

    # Audit log
    await create_audit_log(
        db,
        tenant_id=current_user["tenant_id"],
        actor_id=current_user["user_id"],
        action="PR_REJECTED",
        entity_type="PR",
        entity_id=str(pr.id),
        before_state=before,
        after_state=after,
        actor_email=current_user.get("email"),
    )

    await db.flush()

    # Notify requester
    requester_result = await db.execute(
        select(User).where(User.id == pr.requester_id)
    )
    requester = requester_result.scalar_one_or_none()
    if requester:
        background_tasks.add_task(
            send_notification,
            template_id="pr_rejected",
            recipient_emails=[requester.email],
            context={
                "pr_number": pr.pr_number,
                "reason": body.reason,
            },
        )

    line_items = await _get_line_items(db, pr.id)
    logger.info("pr_rejected", pr_id=str(pr.id), by=current_user["user_id"])
    return _to_response(pr, line_items)
