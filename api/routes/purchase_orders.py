from datetime import datetime, date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.middleware.auth import get_current_user
from api.middleware.tenant import get_db_with_tenant
from api.middleware.authorization import require_roles
from api.models.purchase_order import PurchaseOrder, PoLineItem
from api.models.purchase_request import PurchaseRequest, PrLineItem
from api.models.vendor import Vendor
from api.schemas.purchase_order import (
    PurchaseOrderCreate,
    PurchaseOrderResponse,
    PoLineItemResponse,
    CancelRequest,
)
from api.schemas.common import PaginatedResponse, build_pagination
from api.services.budget_service import release_budget_reservation
from api.services.audit_service import create_audit_log

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


def _to_response(po: PurchaseOrder, line_items: list[PoLineItem]) -> PurchaseOrderResponse:
    return PurchaseOrderResponse(
        id=str(po.id),
        tenant_id=str(po.tenant_id),
        po_number=po.po_number,
        pr_id=str(po.pr_id) if po.pr_id else None,
        vendor_id=str(po.vendor_id),
        status=po.status,
        total_cents=po.total_cents,
        currency=po.currency,
        expected_delivery_date=(
            po.expected_delivery_date.isoformat() if po.expected_delivery_date else None
        ),
        terms_and_conditions=po.terms_and_conditions,
        line_items=[_line_to_response(li) for li in line_items],
        created_at=po.created_at.isoformat() if po.created_at else "",
        updated_at=po.updated_at.isoformat() if po.updated_at else "",
    )


async def _get_line_items(db: AsyncSession, po_id) -> list[PoLineItem]:
    result = await db.execute(
        select(PoLineItem).where(PoLineItem.po_id == po_id).order_by(PoLineItem.line_number)
    )
    return list(result.scalars().all())


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

    if po_status:
        q = q.where(PurchaseOrder.status == po_status)
        count_q = count_q.where(PurchaseOrder.status == po_status)
    if vendor_id:
        q = q.where(PurchaseOrder.vendor_id == vendor_id)
        count_q = count_q.where(PurchaseOrder.vendor_id == vendor_id)
    if pr_id:
        q = q.where(PurchaseOrder.pr_id == pr_id)
        count_q = count_q.where(PurchaseOrder.pr_id == pr_id)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        q.order_by(PurchaseOrder.created_at.desc()).offset((page - 1) * limit).limit(limit)
    )
    pos = result.scalars().all()

    items = []
    for po in pos:
        line_items = await _get_line_items(db, po.id)
        items.append(_to_response(po, line_items))

    return PaginatedResponse(data=items, pagination=build_pagination(page, limit, total))


@router.get("/{po_id}", response_model=PurchaseOrderResponse)
async def get_purchase_order(
    po_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.id == po_id, PurchaseOrder.deleted_at == None  # noqa: E711
        )
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    line_items = await _get_line_items(db, po.id)
    return _to_response(po, line_items)


@router.post("", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    body: PurchaseOrderCreate,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("procurement", "procurement_lead", "admin")),
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
    logger.info("po_created", po_id=str(po.id), po_number=po.po_number, pr_id=str(pr.id))
    return _to_response(po, line_items)


@router.post("/{po_id}/acknowledge", response_model=PurchaseOrderResponse)
async def acknowledge_purchase_order(
    po_id: str,
    current_user: dict = Depends(get_current_user),
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

    if po.status != "ISSUED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only acknowledge purchase orders in ISSUED status",
        )

    po.status = "ACKNOWLEDGED"
    await db.flush()
    line_items = await _get_line_items(db, po.id)
    return _to_response(po, line_items)


@router.post("/{po_id}/cancel", response_model=PurchaseOrderResponse)
async def cancel_purchase_order(
    po_id: str,
    body: CancelRequest,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("procurement", "procurement_lead", "admin")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.id == po_id, PurchaseOrder.deleted_at == None  # noqa: E711
        )
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

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
    return _to_response(po, line_items)
