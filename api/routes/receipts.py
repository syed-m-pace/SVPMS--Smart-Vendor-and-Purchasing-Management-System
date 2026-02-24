from datetime import datetime, date as date_type

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.middleware.auth import get_current_user
from api.middleware.tenant import get_db_with_tenant
from api.middleware.authorization import require_roles
from api.models.invoice import Invoice
from api.models.receipt import Receipt, ReceiptLineItem
from api.models.purchase_order import PurchaseOrder, PoLineItem
from api.schemas.receipt import (
    ReceiptCreate,
    ReceiptResponse,
    ReceiptLineItemResponse,
)
from api.schemas.common import PaginatedResponse, build_pagination

logger = structlog.get_logger()
router = APIRouter()

RECEIPT_PREFIX = "GRN"


async def _generate_receipt_number(db: AsyncSession) -> str:
    result = await db.execute(select(func.count(Receipt.id)))
    count = (result.scalar() or 0) + 1
    return f"{RECEIPT_PREFIX}-{count:06d}"


def _line_to_response(li: ReceiptLineItem) -> ReceiptLineItemResponse:
    return ReceiptLineItemResponse(
        id=str(li.id),
        po_line_item_id=str(li.po_line_item_id),
        quantity_received=li.quantity_received,
        condition=li.condition,
        notes=li.notes,
    )


def _to_response(r: Receipt, line_items: list[ReceiptLineItem]) -> ReceiptResponse:
    return ReceiptResponse(
        id=str(r.id),
        tenant_id=str(r.tenant_id),
        receipt_number=r.receipt_number,
        po_id=str(r.po_id),
        received_by=str(r.received_by),
        receipt_date=r.receipt_date.isoformat() if r.receipt_date else "",
        status=r.status,
        notes=r.notes,
        document_key=r.document_key,
        line_items=[_line_to_response(li) for li in line_items],
        created_at=r.created_at.isoformat() if r.created_at else "",
    )


async def _get_line_items(db: AsyncSession, receipt_id) -> list[ReceiptLineItem]:
    result = await db.execute(
        select(ReceiptLineItem).where(ReceiptLineItem.receipt_id == receipt_id)
    )
    return list(result.scalars().all())


@router.get("", response_model=PaginatedResponse[ReceiptResponse])
async def list_receipts(
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=25),
    po_id: str = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    q = select(Receipt)
    count_q = select(func.count(Receipt.id))

    if po_id:
        q = q.where(Receipt.po_id == po_id)
        count_q = count_q.where(Receipt.po_id == po_id)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        q.order_by(Receipt.created_at.desc()).offset((page - 1) * limit).limit(limit)
    )
    receipts = result.scalars().all()

    # Batch-load all line items in a single query instead of N per-receipt queries
    receipt_ids = [r.id for r in receipts]
    li_map: dict = {}
    if receipt_ids:
        li_result = await db.execute(
            select(ReceiptLineItem).where(ReceiptLineItem.receipt_id.in_(receipt_ids))
        )
        for li in li_result.scalars().all():
            li_map.setdefault(str(li.receipt_id), []).append(li)

    items = []
    for r in receipts:
        items.append(_to_response(r, li_map.get(str(r.id), [])))

    return PaginatedResponse(data=items, pagination=build_pagination(page, limit, total))


@router.get("/{receipt_id}", response_model=ReceiptResponse)
async def get_receipt(
    receipt_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(select(Receipt).where(Receipt.id == receipt_id))
    receipt = result.scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    line_items = await _get_line_items(db, receipt.id)
    return _to_response(receipt, line_items)


@router.post("", response_model=ReceiptResponse, status_code=status.HTTP_201_CREATED)
async def create_receipt(
    body: ReceiptCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("procurement", "procurement_lead", "admin", "manager")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    # Validate PO exists and is in receivable status
    po_result = await db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.id == body.po_id, PurchaseOrder.deleted_at == None  # noqa: E711
        )
    )
    po = po_result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    if po.status not in ("ISSUED", "ACKNOWLEDGED", "PARTIALLY_FULFILLED"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot create receipt for PO in '{po.status}' status",
        )

    # Validate line items reference valid PO line items
    po_lines_result = await db.execute(
        select(PoLineItem).where(PoLineItem.po_id == po.id)
    )
    po_lines_map = {str(li.id): li for li in po_lines_result.scalars().all()}

    for rli in body.line_items:
        if rli.po_line_item_id not in po_lines_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"PO line item '{rli.po_line_item_id}' not found on this PO",
            )
        po_li = po_lines_map[rli.po_line_item_id]
        remaining = po_li.quantity - (po_li.received_quantity or 0)
        if rli.quantity_received > remaining:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Quantity received ({rli.quantity_received}) exceeds remaining "
                    f"({remaining}) for PO line item '{rli.po_line_item_id}'"
                ),
            )

    receipt_number = await _generate_receipt_number(db)

    receipt = Receipt(
        tenant_id=current_user["tenant_id"],
        receipt_number=receipt_number,
        po_id=po.id,
        received_by=current_user["user_id"],
        receipt_date=date_type.today(),
        status="CONFIRMED",
        notes=body.notes,
        document_key=body.document_key,
    )
    db.add(receipt)
    await db.flush()

    for rli_data in body.line_items:
        rli = ReceiptLineItem(
            receipt_id=receipt.id,
            po_line_item_id=rli_data.po_line_item_id,
            quantity_received=rli_data.quantity_received,
            condition=rli_data.condition,
            notes=rli_data.notes,
        )
        db.add(rli)

        # Update PO line item received_quantity
        po_li = po_lines_map[rli_data.po_line_item_id]
        po_li.received_quantity = (po_li.received_quantity or 0) + rli_data.quantity_received

    # Check if PO is fully fulfilled
    all_po_lines = await db.execute(
        select(PoLineItem).where(PoLineItem.po_id == po.id)
    )
    all_fulfilled = all(
        (li.received_quantity or 0) >= li.quantity
        for li in all_po_lines.scalars().all()
    )
    if all_fulfilled:
        po.status = "FULFILLED"
    else:
        po.status = "PARTIALLY_FULFILLED"

    await db.flush()
    await db.refresh(receipt)
    line_items = await _get_line_items(db, receipt.id)
    logger.info("receipt_created", receipt_id=str(receipt.id), po_id=str(po.id))

    # Trigger 3-way match for any open invoices against this PO
    from api.jobs.three_way_match import run_three_way_match
    invoice_result = await db.execute(
        select(Invoice).where(
            Invoice.po_id == po.id,
            Invoice.status.in_(["UPLOADED", "EXCEPTION"]),
            Invoice.deleted_at == None,  # noqa: E711
        )
    )
    for inv in invoice_result.scalars().all():
        background_tasks.add_task(
            run_three_way_match, str(inv.id), str(current_user["tenant_id"])
        )

    return _to_response(receipt, line_items)
