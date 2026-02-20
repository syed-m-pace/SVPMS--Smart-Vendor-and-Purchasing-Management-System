from datetime import datetime, date as date_type
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import case, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.middleware.auth import get_current_user
from api.middleware.tenant import get_db_with_tenant
from api.middleware.authorization import require_roles
from api.models.purchase_order import PurchaseOrder, PoLineItem
from api.models.purchase_request import PurchaseRequest, PrLineItem
from api.models.user import User
from api.models.vendor import Vendor
from api.schemas.purchase_order import (
    PurchaseOrderCreate,
    PurchaseOrderReadyResponse,
    PurchaseOrderResponse,
    PoLineItemResponse,
    CancelRequest,
    AcknowledgeRequest,
)
from api.schemas.common import PaginatedResponse, build_pagination
from api.services.budget_service import release_budget_reservation
from api.services.audit_service import create_audit_log
from api.services.notification_service import send_notification
from api.services.push_service import send_push

logger = structlog.get_logger()
router = APIRouter()

PO_PREFIX = "PO"


async def _generate_po_number(db: AsyncSession) -> str:
    result = await db.execute(select(func.count(PurchaseOrder.id)))
    count = (result.scalar() or 0) + 1
    return f"{PO_PREFIX}-{count:06d}"


def _line_to_response(li: PoLineItem) -> PoLineItemResponse:
    return PoLineItemResponse(
        id=str(li.id),
        line_number=li.line_number,
        description=li.description,
        quantity=li.quantity,
        unit_price_cents=li.unit_price_cents,
        received_quantity=li.received_quantity or 0,
    )


def _to_response(po: PurchaseOrder, line_items: list[PoLineItem], vendor_name: Optional[str] = None) -> PurchaseOrderResponse:
    return PurchaseOrderResponse(
        id=str(po.id),
        tenant_id=str(po.tenant_id),
        po_number=po.po_number,
        pr_id=str(po.pr_id) if po.pr_id else None,
        vendor_id=str(po.vendor_id),
        vendor_name=vendor_name,
        status=po.status,
        total_cents=po.total_cents,
        currency=po.currency,
        issued_at=po.issued_at.isoformat() if po.issued_at else None,
        expected_delivery_date=(
            po.expected_delivery_date.isoformat() if po.expected_delivery_date else None
        ),
        terms_and_conditions=po.terms_and_conditions,
        line_items=[_line_to_response(li) for li in line_items],
        created_at=po.created_at.isoformat() if po.created_at else "",
        updated_at=po.updated_at.isoformat() if po.updated_at else "",
    )


def _ready_to_response(pr: PurchaseRequest) -> PurchaseOrderReadyResponse:
    return PurchaseOrderReadyResponse(
        pr_id=str(pr.id),
        pr_number=pr.pr_number,
        requester_id=str(pr.requester_id),
        department_id=str(pr.department_id),
        total_cents=pr.total_cents,
        currency=pr.currency,
        description=pr.description,
        approved_at=pr.approved_at.isoformat() if pr.approved_at else None,
        created_at=pr.created_at.isoformat() if pr.created_at else "",
    )


async def _get_line_items(db: AsyncSession, po_id) -> list[PoLineItem]:
    result = await db.execute(
        select(PoLineItem).where(PoLineItem.po_id == po_id).order_by(PoLineItem.line_number)
    )
    return list(result.scalars().all())


async def _resolve_vendor_for_user(
    db: AsyncSession, current_user: dict
) -> Optional[Vendor]:
    result = await db.execute(
        select(Vendor)
        .where(
            Vendor.tenant_id == current_user["tenant_id"],
            Vendor.email == current_user["email"],
            Vendor.deleted_at == None,  # noqa: E711
        )
        .order_by(
            case((Vendor.status == "ACTIVE", 0), else_=1),
            Vendor.created_at.asc(),
        )
    )
    return result.scalars().first()


@router.get("", response_model=PaginatedResponse[PurchaseOrderResponse])
async def list_purchase_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    po_status: str = Query(None, alias="status"),
    vendor_id: str = Query(None),
    pr_id: str = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    q = select(PurchaseOrder).where(PurchaseOrder.deleted_at == None)  # noqa: E711
    count_q = select(func.count(PurchaseOrder.id)).where(PurchaseOrder.deleted_at == None)  # noqa: E711

    scoped_vendor_id = None
    if current_user["role"] == "vendor":
        vendor = await _resolve_vendor_for_user(db, current_user)
        if not vendor:
            return PaginatedResponse(
                data=[],
                pagination=build_pagination(page, limit, 0),
            )
        scoped_vendor_id = vendor.id

    if po_status:
        q = q.where(PurchaseOrder.status == po_status)
        count_q = count_q.where(PurchaseOrder.status == po_status)
    if scoped_vendor_id is not None:
        q = q.where(PurchaseOrder.vendor_id == scoped_vendor_id)
        count_q = count_q.where(PurchaseOrder.vendor_id == scoped_vendor_id)
    elif vendor_id:
        q = q.where(PurchaseOrder.vendor_id == vendor_id)
        count_q = count_q.where(PurchaseOrder.vendor_id == vendor_id)
    if pr_id:
        q = q.where(PurchaseOrder.pr_id == pr_id)
        count_q = count_q.where(PurchaseOrder.pr_id == pr_id)

    total = (await db.execute(count_q)).scalar() or 0
    q = q.add_columns(Vendor.legal_name).join(Vendor, PurchaseOrder.vendor_id == Vendor.id)
    result = await db.execute(
        q.order_by(PurchaseOrder.created_at.desc()).offset((page - 1) * limit).limit(limit)
    )
    rows = result.all()

    items = []
    for row in rows:
        po, vendor_name = row[0], row[1]
        line_items = await _get_line_items(db, po.id)
        items.append(_to_response(po, line_items, vendor_name=vendor_name))

    return PaginatedResponse(data=items, pagination=build_pagination(page, limit, total))


@router.get("/ready", response_model=PaginatedResponse[PurchaseOrderReadyResponse])
async def list_ready_purchase_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(
        require_roles(
            "procurement",
            "procurement_lead",
            "admin",
            "manager",
            "finance",
            "finance_head",
            "cfo",
        )
    ),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    active_po_exists = exists(
        select(PurchaseOrder.id).where(
            PurchaseOrder.pr_id == PurchaseRequest.id,
            PurchaseOrder.deleted_at == None,  # noqa: E711
            PurchaseOrder.status != "CANCELLED",
        )
    )

    q = select(PurchaseRequest).where(
        PurchaseRequest.deleted_at == None,  # noqa: E711
        PurchaseRequest.status == "APPROVED",
        ~active_po_exists,
    )
    count_q = select(func.count(PurchaseRequest.id)).where(
        PurchaseRequest.deleted_at == None,  # noqa: E711
        PurchaseRequest.status == "APPROVED",
        ~active_po_exists,
    )

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        q.order_by(PurchaseRequest.approved_at.desc(), PurchaseRequest.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    prs = result.scalars().all()

    return PaginatedResponse(
        data=[_ready_to_response(pr) for pr in prs],
        pagination=build_pagination(page, limit, total),
    )


@router.get("/{po_id}", response_model=PurchaseOrderResponse)
async def get_purchase_order(
    po_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(
        select(PurchaseOrder, Vendor.legal_name).join(Vendor, PurchaseOrder.vendor_id == Vendor.id).where(
            PurchaseOrder.id == po_id, PurchaseOrder.deleted_at == None  # noqa: E711
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    po, vendor_name = row

    if current_user["role"] == "vendor":
        vendor = await _resolve_vendor_for_user(db, current_user)
        if not vendor or po.vendor_id != vendor.id:
            raise HTTPException(status_code=404, detail="Purchase order not found")

    line_items = await _get_line_items(db, po.id)
    return _to_response(po, line_items, vendor_name=vendor_name)


@router.post("", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    body: PurchaseOrderCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("procurement", "procurement_lead", "admin", "manager", "finance", "finance_head", "cfo")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    # Validate PR exists and is APPROVED
    pr_result = await db.execute(
        select(PurchaseRequest).where(
            PurchaseRequest.id == body.pr_id,
            PurchaseRequest.deleted_at == None,  # noqa: E711
        )
    )
    pr = pr_result.scalar_one_or_none()
    if not pr:
        raise HTTPException(status_code=404, detail="Purchase request not found")
    if pr.status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Purchase request must be APPROVED to create a PO",
        )

    # Validate vendor exists and is ACTIVE
    vendor_result = await db.execute(
        select(Vendor).where(
            Vendor.id == body.vendor_id, Vendor.deleted_at == None  # noqa: E711
        )
    )
    vendor = vendor_result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    if vendor.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vendor must be ACTIVE to create a PO",
        )

    # Check no existing PO for this PR
    existing_po = await db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.pr_id == body.pr_id,
            PurchaseOrder.status.notin_(["CANCELLED"]),
            PurchaseOrder.deleted_at == None,  # noqa: E711
        )
    )
    if existing_po.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A purchase order already exists for this purchase request",
        )

    po_number = await _generate_po_number(db)

    # Parse expected delivery date
    delivery_date = None
    if body.expected_delivery_date:
        try:
            delivery_date = date_type.fromisoformat(body.expected_delivery_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid expected_delivery_date format (use YYYY-MM-DD)",
            )

    po = PurchaseOrder(
        tenant_id=current_user["tenant_id"],
        po_number=po_number,
        pr_id=pr.id,
        vendor_id=vendor.id,
        status="ISSUED",
        issued_at=datetime.utcnow(),
        total_cents=pr.total_cents,
        currency=pr.currency,
        expected_delivery_date=delivery_date,
        terms_and_conditions=body.terms_and_conditions,
    )
    db.add(po)
    await db.flush()

    # Copy line items from PR
    pr_lines = await db.execute(
        select(PrLineItem).where(PrLineItem.pr_id == pr.id).order_by(PrLineItem.line_number)
    )
    for pr_li in pr_lines.scalars().all():
        po_li = PoLineItem(
            po_id=po.id,
            line_number=pr_li.line_number,
            description=pr_li.description,
            quantity=pr_li.quantity,
            unit_price_cents=pr_li.unit_price_cents,
            received_quantity=0,
        )
        db.add(po_li)

    await db.flush()
    line_items = await _get_line_items(db, po.id)

    # Notify vendor via push + email. Failures should not block PO creation.
    try:
        vendor_user_ids_result = await db.execute(
            select(User.id).where(
                User.email == vendor.email,
                User.role == "vendor",
                User.is_active == True,  # noqa: E712
                User.deleted_at == None,  # noqa: E711
            )
        )
        vendor_user_ids = [str(row[0]) for row in vendor_user_ids_result.all()]
        if vendor_user_ids:
            await send_push(
                db,
                user_ids=vendor_user_ids,
                title="New purchase order issued",
                body=f"{po.po_number} has been issued to your account.",
                data={
                    "type": "NEW_PO",
                    "id": str(po.id),
                    "po_id": str(po.id),
                    "po_number": po.po_number,
                },
            )

        background_tasks.add_task(
            send_notification,
            "po_issued",
            [vendor.email],
            {
                "po_number": po.po_number,
                "currency": po.currency,
                "amount_cents": po.total_cents,
            },
        )
    except Exception as exc:
        logger.error(
            "po_vendor_notification_failed",
            po_id=str(po.id),
            vendor_id=str(vendor.id),
            error=str(exc),
        )

    logger.info("po_created", po_id=str(po.id), po_number=po.po_number, pr_id=str(pr.id))
    return _to_response(po, line_items, vendor_name=vendor.legal_name)


@router.post("/{po_id}/acknowledge", response_model=PurchaseOrderResponse)
async def acknowledge_purchase_order(
    po_id: str,
    body: AcknowledgeRequest,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("vendor")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    """Vendor acknowledges a purchase order."""
    result = await db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.id == po_id, PurchaseOrder.deleted_at == None  # noqa: E711
        )
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    vendor = await _resolve_vendor_for_user(db, current_user)
    if not vendor or po.vendor_id != vendor.id:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    if po.status != "ISSUED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only acknowledge purchase orders in ISSUED status",
        )

    if body.expected_delivery_date:
        try:
            po.expected_delivery_date = datetime.fromisoformat(body.expected_delivery_date)
        except ValueError:
            pass # Invalid format, ignore or handle elsewhere

    po.status = "ACKNOWLEDGED"
    await db.flush()
    line_items = await _get_line_items(db, po.id)
    return _to_response(po, line_items, vendor_name=vendor.legal_name)


@router.post("/{po_id}/cancel", response_model=PurchaseOrderResponse)
async def cancel_purchase_order(
    po_id: str,
    body: CancelRequest,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("procurement", "procurement_lead", "admin")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(
        select(PurchaseOrder, Vendor.legal_name).join(Vendor, PurchaseOrder.vendor_id == Vendor.id).where(
            PurchaseOrder.id == po_id, PurchaseOrder.deleted_at == None  # noqa: E711
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Purchase order not found")
        
    po, vendor_name = row

    if po.status in ("FULFILLED", "CLOSED", "CANCELLED"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel purchase order in '{po.status}' status",
        )

    before = {"status": po.status}
    po.status = "CANCELLED"
    after = {"status": po.status}

    # Release budget reservation held by the parent PR
    if po.pr_id:
        await release_budget_reservation(db, "PR", str(po.pr_id))

    await create_audit_log(
        db,
        tenant_id=current_user["tenant_id"],
        actor_id=current_user["user_id"],
        action="PO_CANCELLED",
        entity_type="PO",
        entity_id=str(po.id),
        before_state=before,
        after_state=after,
        actor_email=current_user.get("email"),
    )

    await db.flush()
    line_items = await _get_line_items(db, po.id)
    logger.info("po_cancelled", po_id=str(po.id), reason=body.reason, by=current_user["user_id"])
    return _to_response(po, line_items, vendor_name=vendor_name)
