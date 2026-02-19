from datetime import date as date_type

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.middleware.auth import get_current_user
from api.middleware.tenant import get_db_with_tenant
from api.middleware.authorization import require_roles
from api.models.invoice import Invoice, InvoiceLineItem
from api.models.purchase_order import PurchaseOrder
from api.schemas.invoice import (
    InvoiceCreate,
    InvoiceResponse,
    InvoiceLineItemResponse,
    InvoiceDisputeRequest,
    InvoiceOverrideRequest,
)
from api.schemas.common import PaginatedResponse, build_pagination
from api.services.audit_service import create_audit_log
from api.services.storage import r2_client

logger = structlog.get_logger()
router = APIRouter()


def _line_to_response(li: InvoiceLineItem) -> InvoiceLineItemResponse:
    return InvoiceLineItemResponse(
        id=str(li.id),
        line_number=li.line_number,
        description=li.description,
        quantity=li.quantity,
        unit_price_cents=li.unit_price_cents,
    )


def _to_response(inv: Invoice, line_items: list[InvoiceLineItem]) -> InvoiceResponse:
    return InvoiceResponse(
        id=str(inv.id),
        tenant_id=str(inv.tenant_id),
        invoice_number=inv.invoice_number,
        po_id=str(inv.po_id) if inv.po_id else None,
        vendor_id=str(inv.vendor_id),
        status=inv.status,
        invoice_date=inv.invoice_date.isoformat() if inv.invoice_date else "",
        due_date=inv.due_date.isoformat() if inv.due_date else None,
        total_cents=inv.total_cents,
        currency=inv.currency,
        document_url=inv.document_url,
        match_status=inv.match_status,
        ocr_status=inv.ocr_status,
        ocr_data=inv.ocr_data,
        match_exceptions=inv.match_exceptions,
        line_items=[_line_to_response(li) for li in line_items],
        created_at=inv.created_at.isoformat() if inv.created_at else "",
        updated_at=inv.updated_at.isoformat() if inv.updated_at else "",
    )


async def _get_line_items(db: AsyncSession, invoice_id) -> list[InvoiceLineItem]:
    result = await db.execute(
        select(InvoiceLineItem)
        .where(InvoiceLineItem.invoice_id == invoice_id)
        .order_by(InvoiceLineItem.line_number)
    )
    return list(result.scalars().all())


@router.get("", response_model=PaginatedResponse[InvoiceResponse])
async def list_invoices(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    inv_status: str = Query(None, alias="status"),
    vendor_id: str = Query(None),
    po_id: str = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    q = select(Invoice)
    count_q = select(func.count(Invoice.id))

    if inv_status:
        q = q.where(Invoice.status == inv_status)
        count_q = count_q.where(Invoice.status == inv_status)
    if vendor_id:
        q = q.where(Invoice.vendor_id == vendor_id)
        count_q = count_q.where(Invoice.vendor_id == vendor_id)
    if po_id:
        q = q.where(Invoice.po_id == po_id)
        count_q = count_q.where(Invoice.po_id == po_id)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        q.order_by(Invoice.created_at.desc()).offset((page - 1) * limit).limit(limit)
    )
    invoices = result.scalars().all()

    items = []
    for inv in invoices:
        line_items = await _get_line_items(db, inv.id)
        items.append(_to_response(inv, line_items))

    return PaginatedResponse(data=items, pagination=build_pagination(page, limit, total))


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    line_items = await _get_line_items(db, inv.id)
    return _to_response(inv, line_items)


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    body: InvoiceCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("vendor", "finance", "admin")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    # Validate PO exists
    po_result = await db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.id == body.po_id, PurchaseOrder.deleted_at == None  # noqa: E711
        )
    )
    po = po_result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    # Check duplicate invoice_number for this vendor
    existing = await db.execute(
        select(Invoice).where(
            Invoice.invoice_number == body.invoice_number,
            Invoice.vendor_id == po.vendor_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invoice with this number already exists for this vendor",
        )

    # Parse dates
    try:
        invoice_date = date_type.fromisoformat(body.invoice_date)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invoice_date format (use YYYY-MM-DD)",
        )

    due_date = None
    if body.due_date:
        try:
            due_date = date_type.fromisoformat(body.due_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid due_date format (use YYYY-MM-DD)",
            )

    inv = Invoice(
        tenant_id=current_user["tenant_id"],
        invoice_number=body.invoice_number,
        po_id=po.id,
        vendor_id=po.vendor_id,
        status="UPLOADED",
        invoice_date=invoice_date,
        due_date=due_date,
        total_cents=body.total_cents,
        currency=po.currency,
    )
    db.add(inv)
    await db.flush()

    # Create line items
    for idx, li_data in enumerate(body.line_items, start=1):
        li = InvoiceLineItem(
            invoice_id=inv.id,
            line_number=idx,
            description=li_data.description,
            quantity=li_data.quantity,
            unit_price_cents=li_data.unit_price_cents,
        )
        db.add(li)

    await db.flush()
    line_items = await _get_line_items(db, inv.id)
    logger.info("invoice_created", invoice_id=str(inv.id), po_id=str(po.id))

    # Normalize document reference and queue OCR if available.
    raw_document_ref = body.document_key or body.document_url
    if raw_document_ref:
        document_key = r2_client.extract_key(raw_document_ref)
        if not document_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid invoice document reference",
            )
        inv.document_url = document_key
        await db.flush()
        from api.jobs.invoice_ocr import process_invoice_ocr
        background_tasks.add_task(
            process_invoice_ocr, str(inv.id), str(current_user["tenant_id"])
        )
        logger.info("ocr_queued", invoice_id=str(inv.id))

    return _to_response(inv, line_items)


@router.post("/{invoice_id}/dispute", response_model=InvoiceResponse)
async def dispute_invoice(
    invoice_id: str,
    body: InvoiceDisputeRequest,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("vendor")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if inv.status != "EXCEPTION":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only dispute invoices in EXCEPTION status",
        )

    before = {"status": inv.status}
    inv.status = "DISPUTED"
    after = {"status": inv.status}

    await create_audit_log(
        db,
        tenant_id=current_user["tenant_id"],
        actor_id=current_user["user_id"],
        action="INVOICE_DISPUTED",
        entity_type="INVOICE",
        entity_id=str(inv.id),
        before_state=before,
        after_state=after,
        actor_email=current_user.get("email"),
    )

    await db.flush()
    line_items = await _get_line_items(db, inv.id)
    logger.info("invoice_disputed", invoice_id=str(inv.id), reason=body.reason)
    return _to_response(inv, line_items)


@router.post("/{invoice_id}/override", response_model=InvoiceResponse)
async def override_invoice(
    invoice_id: str,
    body: InvoiceOverrideRequest,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("finance_head", "cfo", "admin")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if inv.status not in ("EXCEPTION", "DISPUTED"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only override invoices in EXCEPTION or DISPUTED status",
        )

    before = {"status": inv.status, "match_status": inv.match_status}
    inv.status = "MATCHED"
    inv.match_status = "OVERRIDE"
    after = {"status": inv.status, "match_status": inv.match_status}

    await create_audit_log(
        db,
        tenant_id=current_user["tenant_id"],
        actor_id=current_user["user_id"],
        action="INVOICE_OVERRIDDEN",
        entity_type="INVOICE",
        entity_id=str(inv.id),
        before_state=before,
        after_state=after,
        actor_email=current_user.get("email"),
    )

    await db.flush()
    line_items = await _get_line_items(db, inv.id)
    logger.info("invoice_overridden", invoice_id=str(inv.id), reason=body.reason, by=current_user["user_id"])
    return _to_response(inv, line_items)
