from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.middleware.auth import get_current_user
from api.middleware.tenant import get_db_with_tenant
from api.middleware.authorization import require_roles
from api.models.rfq import Rfq, RfqLineItem, RfqBid
from api.models.vendor import Vendor
from api.models.user import User
from api.models.purchase_order import PurchaseOrder, PoLineItem
from api.services.notification_service import send_notification
from api.services.push_service import send_push
from api.schemas.rfq import (
    RfqCreate,
    RfqResponse,
    RfqLineItemResponse,
    RfqBidCreate,
    RfqBidResponse,
    RfqAwardRequest,
)
from api.schemas.purchase_order import PurchaseOrderResponse, PoLineItemResponse
from api.schemas.common import PaginatedResponse, build_pagination

logger = structlog.get_logger()
router = APIRouter()

RFQ_PREFIX = "RFQ"


async def _generate_rfq_number(db: AsyncSession) -> str:
    result = await db.execute(select(func.count(Rfq.id)))
    count = (result.scalar() or 0) + 1
    return f"{RFQ_PREFIX}-{count:06d}"


def _line_to_response(li: RfqLineItem) -> RfqLineItemResponse:
    return RfqLineItemResponse(
        id=str(li.id),
        description=li.description,
        quantity=li.quantity,
        specifications=li.specifications,
    )


def _bid_to_response(b: RfqBid) -> RfqBidResponse:
    return RfqBidResponse(
        id=str(b.id),
        rfq_id=str(b.rfq_id),
        vendor_id=str(b.vendor_id),
        total_cents=b.total_cents,
        delivery_days=b.delivery_days,
        notes=b.notes,
        score=float(b.score) if b.score is not None else None,
        submitted_at=b.submitted_at.isoformat() if b.submitted_at else "",
    )


async def _build_response(db: AsyncSession, rfq: Rfq, current_user: dict = None) -> RfqResponse:
    lines_result = await db.execute(
        select(RfqLineItem).where(RfqLineItem.rfq_id == rfq.id)
    )
    
    bids_query = select(RfqBid).where(RfqBid.rfq_id == rfq.id).order_by(RfqBid.total_cents)
    
    if current_user and current_user.get("role") == "vendor":
        from api.models.vendor import Vendor
        vendor_result = await db.execute(
            select(Vendor).where(Vendor.email == current_user["email"])
        )
        vendor = vendor_result.scalar_one_or_none()
        if vendor:
            bids_query = bids_query.where(RfqBid.vendor_id == str(vendor.id))
        else:
            bids_query = bids_query.where(RfqBid.vendor_id == "00000000-0000-0000-0000-000000000000")
            
    bids_result = await db.execute(bids_query)
    return RfqResponse(
        id=str(rfq.id),
        tenant_id=str(rfq.tenant_id),
        rfq_number=rfq.rfq_number,
        title=rfq.title,
        pr_id=str(rfq.pr_id) if rfq.pr_id else None,
        status=rfq.status,
        deadline=rfq.deadline.isoformat() if rfq.deadline else "",
        created_by=str(rfq.created_by),
        awarded_vendor_id=str(rfq.awarded_vendor_id) if rfq.awarded_vendor_id else None,
        awarded_po_id=str(rfq.awarded_po_id) if rfq.awarded_po_id else None,
        line_items=[_line_to_response(li) for li in lines_result.scalars().all()],
        bids=[_bid_to_response(b) for b in bids_result.scalars().all()],
        created_at=rfq.created_at.isoformat() if rfq.created_at else "",
    )


@router.get("", response_model=PaginatedResponse[RfqResponse])
async def list_rfqs(
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=50),
    rfq_status: str = Query(None, alias="status"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    q = select(Rfq)
    count_q = select(func.count(Rfq.id))

    # Resolve vendor once for scoping and bid filtering
    scoped_vendor = None
    if current_user["role"] == "vendor":
        vendor_result = await db.execute(
            select(Vendor).where(
                Vendor.email == current_user["email"],
                Vendor.deleted_at == None,  # noqa: E711
            )
        )
        scoped_vendor = vendor_result.scalar_one_or_none()
        if not scoped_vendor:
            return PaginatedResponse(data=[], pagination=build_pagination(page, limit, 0))
        vendor_filter = or_(
            Rfq.status == "OPEN",
            (Rfq.status == "AWARDED") & (Rfq.awarded_vendor_id == scoped_vendor.id),
        )
        q = q.where(vendor_filter)
        count_q = count_q.where(vendor_filter)
        if rfq_status:
            q = q.where(Rfq.status == rfq_status)
            count_q = count_q.where(Rfq.status == rfq_status)
    elif rfq_status:
        q = q.where(Rfq.status == rfq_status)
        count_q = count_q.where(Rfq.status == rfq_status)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        q.order_by(Rfq.created_at.desc()).offset((page - 1) * limit).limit(limit)
    )
    rfqs = result.scalars().all()

    # Batch-load line items and bids for all RFQs — avoids N+1 queries
    rfq_ids = [rfq.id for rfq in rfqs]
    li_map: dict = {}
    bids_map: dict = {}

    if rfq_ids:
        li_result = await db.execute(
            select(RfqLineItem).where(RfqLineItem.rfq_id.in_(rfq_ids))
        )
        for li in li_result.scalars().all():
            li_map.setdefault(str(li.rfq_id), []).append(li)

        bids_q = (
            select(RfqBid)
            .where(RfqBid.rfq_id.in_(rfq_ids))
            .order_by(RfqBid.total_cents)
        )
        if scoped_vendor is not None:
            bids_q = bids_q.where(RfqBid.vendor_id == str(scoped_vendor.id))
        bids_result = await db.execute(bids_q)
        for b in bids_result.scalars().all():
            bids_map.setdefault(str(b.rfq_id), []).append(b)

    items = [
        RfqResponse(
            id=str(rfq.id),
            tenant_id=str(rfq.tenant_id),
            rfq_number=rfq.rfq_number,
            title=rfq.title,
            pr_id=str(rfq.pr_id) if rfq.pr_id else None,
            status=rfq.status,
            deadline=rfq.deadline.isoformat() if rfq.deadline else "",
            created_by=str(rfq.created_by),
            awarded_vendor_id=str(rfq.awarded_vendor_id) if rfq.awarded_vendor_id else None,
            awarded_po_id=str(rfq.awarded_po_id) if rfq.awarded_po_id else None,
            line_items=[_line_to_response(li) for li in li_map.get(str(rfq.id), [])],
            bids=[_bid_to_response(b) for b in bids_map.get(str(rfq.id), [])],
            created_at=rfq.created_at.isoformat() if rfq.created_at else "",
        )
        for rfq in rfqs
    ]

    return PaginatedResponse(data=items, pagination=build_pagination(page, limit, total))


@router.get("/{rfq_id}", response_model=RfqResponse)
async def get_rfq(
    rfq_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(select(Rfq).where(Rfq.id == rfq_id))
    rfq = result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    return await _build_response(db, rfq, current_user)


@router.post("", response_model=RfqResponse, status_code=status.HTTP_201_CREATED)
async def create_rfq(
    body: RfqCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("procurement", "procurement_lead", "admin", "manager")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    # Parse deadline
    try:
        deadline = datetime.fromisoformat(body.deadline.replace('Z', '+00:00'))
        if deadline.tzinfo is not None:
            deadline = deadline.astimezone(timezone.utc).replace(tzinfo=None)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid deadline format (use ISO 8601)",
        )

    rfq_number = await _generate_rfq_number(db)

    rfq = Rfq(
        tenant_id=current_user["tenant_id"],
        rfq_number=rfq_number,
        title=body.title,
        pr_id=body.pr_id,
        status="OPEN",
        deadline=deadline,
        created_by=current_user["user_id"],
    )
    db.add(rfq)
    await db.flush()

    for li_data in body.line_items:
        li = RfqLineItem(
            rfq_id=rfq.id,
            description=li_data.description,
            quantity=li_data.quantity,
            specifications=li_data.specifications,
        )
        db.add(li)

    await db.flush()
    logger.info("rfq_created", rfq_id=str(rfq.id), rfq_number=rfq.rfq_number)

    # Notify all active vendors in the tenant
    vendor_result = await db.execute(
        select(Vendor).where(
            Vendor.tenant_id == current_user["tenant_id"],
            Vendor.status == "ACTIVE",
            Vendor.deleted_at == None
        )
    )
    vendors = vendor_result.scalars().all()
    
    for vendor in vendors:
        try:
            vendor_user_ids_result = await db.execute(
                select(User.id).where(
                    User.email == vendor.email,
                    User.role == "vendor",
                    User.is_active == True,
                    User.deleted_at == None,
                )
            )
            vendor_user_ids = [str(row[0]) for row in vendor_user_ids_result.all()]
            if vendor_user_ids:
                await send_push(
                    db,
                    user_ids=vendor_user_ids,
                    title="New Request for Quotation",
                    body=f"A new RFQ ({rfq.rfq_number}) has been issued.",
                    data={
                        "type": "NEW_RFQ",
                        "id": str(rfq.id),
                        "rfq_id": str(rfq.id),
                        "rfq_number": rfq.rfq_number,
                    },
                )
            
            background_tasks.add_task(
                send_notification,
                "rfq_issued",
                [vendor.email],
                {
                    "rfq_number": rfq.rfq_number,
                    "title": rfq.title,
                    "deadline": rfq.deadline.strftime("%d %b %Y %H:%M UTC") if rfq.deadline else "—",
                },
            )
        except Exception as exc:
            logger.error("rfq_vendor_notification_failed", rfq_id=str(rfq.id), vendor_id=str(vendor.id), error=str(exc))

    return await _build_response(db, rfq)


@router.post("/{rfq_id}/close", response_model=RfqResponse)
async def close_rfq(
    rfq_id: str,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("procurement", "procurement_lead", "admin")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(select(Rfq).where(Rfq.id == rfq_id))
    rfq = result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")

    if rfq.status != "OPEN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only close RFQs in OPEN status",
        )

    rfq.status = "CLOSED"
    await db.flush()
    return await _build_response(db, rfq)


@router.post("/{rfq_id}/cancel", response_model=RfqResponse)
async def cancel_rfq(
    rfq_id: str,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("procurement", "procurement_lead", "admin")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(select(Rfq).where(Rfq.id == rfq_id))
    rfq = result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")

    if rfq.status not in ("OPEN", "CLOSED"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel RFQ in '{rfq.status}' status (must be OPEN or CLOSED)",
        )

    rfq.status = "CANCELLED"
    await db.flush()
    logger.info("rfq_cancelled", rfq_id=rfq_id, by=current_user["user_id"])
    return await _build_response(db, rfq)


@router.post("/{rfq_id}/bids", response_model=RfqBidResponse, status_code=status.HTTP_201_CREATED)
async def submit_bid(
    rfq_id: str,
    body: RfqBidCreate,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("vendor")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(select(Rfq).where(Rfq.id == rfq_id))
    rfq = result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")

    if rfq.status != "OPEN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only submit bids on OPEN RFQs",
        )

    # Check deadline
    if rfq.deadline and datetime.utcnow() > rfq.deadline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RFQ deadline has passed",
        )

    # Look up vendor record by matching user email → vendor email
    vendor_result = await db.execute(
        select(Vendor).where(Vendor.email == current_user["email"], Vendor.deleted_at == None)  # noqa: E711
    )
    vendor = vendor_result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No vendor record linked to your email address",
        )
    vendor_id = str(vendor.id)

    # Check duplicate bid
    existing = await db.execute(
        select(RfqBid).where(
            RfqBid.rfq_id == rfq_id,
            RfqBid.vendor_id == vendor_id,
        )
    )
    existing_bid = existing.scalar_one_or_none()
    if existing_bid:
        existing_bid.total_cents = body.total_cents
        existing_bid.delivery_days = body.delivery_days
        existing_bid.notes = body.notes
        bid = existing_bid
        await db.flush()
        logger.info("rfq_bid_updated", rfq_id=rfq_id, vendor_id=vendor_id)
        return _bid_to_response(bid)

    bid = RfqBid(
        tenant_id=current_user["tenant_id"],
        rfq_id=rfq.id,
        vendor_id=vendor_id,
        total_cents=body.total_cents,
        delivery_days=body.delivery_days,
        notes=body.notes,
    )
    db.add(bid)
    await db.flush()
    logger.info("rfq_bid_submitted", rfq_id=rfq_id, vendor_id=vendor_id)
    return _bid_to_response(bid)


@router.get("/{rfq_id}/bids", response_model=list[RfqBidResponse])
async def list_bids(
    rfq_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(select(Rfq).where(Rfq.id == rfq_id))
    rfq = result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")

    bids_result = await db.execute(
        select(RfqBid).where(RfqBid.rfq_id == rfq_id).order_by(RfqBid.total_cents)
    )
    return [_bid_to_response(b) for b in bids_result.scalars().all()]


@router.post("/{rfq_id}/award", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
async def award_rfq(
    rfq_id: str,
    body: RfqAwardRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("procurement", "procurement_lead", "admin", "manager")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    """Award an RFQ to the selected bid, creating a PO for the winning vendor."""
    rfq_result = await db.execute(select(Rfq).where(Rfq.id == rfq_id))
    rfq = rfq_result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")

    if rfq.status not in ("OPEN", "CLOSED"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot award an RFQ in '{rfq.status}' status",
        )

    bid_result = await db.execute(
        select(RfqBid).where(RfqBid.id == body.bid_id, RfqBid.rfq_id == rfq.id)
    )
    bid = bid_result.scalar_one_or_none()
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found for this RFQ")

    vendor_result = await db.execute(
        select(Vendor).where(Vendor.id == bid.vendor_id, Vendor.deleted_at == None)  # noqa: E711
    )
    vendor = vendor_result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    if vendor.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vendor must be ACTIVE to receive a PO",
        )

    # Generate PO number
    po_count = (await db.execute(select(func.count(PurchaseOrder.id)))).scalar() or 0
    po_number = f"PO-{(po_count + 1):06d}"

    po = PurchaseOrder(
        tenant_id=current_user["tenant_id"],
        po_number=po_number,
        pr_id=rfq.pr_id,  # may be None — RFQ-sourced POs don't require a PR
        vendor_id=vendor.id,
        status="ISSUED",
        issued_at=datetime.utcnow(),
        total_cents=bid.total_cents,
        currency="INR",
    )
    db.add(po)
    await db.flush()

    # Build PO line items from RFQ line items, distributing bid total by quantity
    rfq_lines_result = await db.execute(
        select(RfqLineItem).where(RfqLineItem.rfq_id == rfq.id).order_by(RfqLineItem.id)
    )
    rfq_lines = list(rfq_lines_result.scalars().all())

    if rfq_lines:
        total_qty = sum(li.quantity for li in rfq_lines)
        allocated = 0
        for idx, li in enumerate(rfq_lines):
            if idx == len(rfq_lines) - 1:
                remaining = bid.total_cents - allocated
                unit_price = max(1, remaining // li.quantity)
            else:
                unit_price = max(1, bid.total_cents // total_qty)
                allocated += unit_price * li.quantity
            db.add(PoLineItem(
                po_id=po.id,
                line_number=idx + 1,
                description=li.description,
                quantity=li.quantity,
                unit_price_cents=unit_price,
                received_quantity=0,
            ))
    else:
        db.add(PoLineItem(
            po_id=po.id,
            line_number=1,
            description=rfq.title,
            quantity=1,
            unit_price_cents=bid.total_cents,
            received_quantity=0,
        ))

    rfq.status = "AWARDED"
    rfq.awarded_vendor_id = vendor.id
    rfq.awarded_po_id = po.id
    await db.flush()

    # Fetch line items for response
    po_lines_result = await db.execute(
        select(PoLineItem).where(PoLineItem.po_id == po.id).order_by(PoLineItem.line_number)
    )
    po_line_items = list(po_lines_result.scalars().all())

    # Notify winning vendor — FCM push + email
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
                title="Congratulations! Your bid was selected",
                body=f"Your bid on {rfq.rfq_number} won. PO {po_number} has been issued to you.",
                data={
                    "type": "RFQ_AWARDED",
                    "id": str(po.id),
                    "po_id": str(po.id),
                    "po_number": po_number,
                    "rfq_id": str(rfq.id),
                    "rfq_number": rfq.rfq_number,
                },
            )

        background_tasks.add_task(
            send_notification,
            "po_awarded",
            [vendor.email],
            {
                "rfq_number": rfq.rfq_number,
                "po_number": po_number,
                "currency": "INR",
                "amount_cents": bid.total_cents,
                "vendor_name": vendor.legal_name,
            },
        )
    except Exception as exc:
        logger.error("award_notification_failed", rfq_id=rfq_id, po_id=str(po.id), error=str(exc))

    logger.info("rfq_awarded", rfq_id=rfq_id, bid_id=str(bid.id), po_id=str(po.id), vendor_id=str(vendor.id))

    return PurchaseOrderResponse(
        id=str(po.id),
        tenant_id=str(po.tenant_id),
        po_number=po.po_number,
        pr_id=str(po.pr_id) if po.pr_id else None,
        vendor_id=str(po.vendor_id),
        vendor_name=vendor.legal_name,
        status=po.status,
        total_cents=po.total_cents,
        currency=po.currency,
        issued_at=po.issued_at.isoformat() if po.issued_at else None,
        expected_delivery_date=None,
        terms_and_conditions=None,
        line_items=[
            PoLineItemResponse(
                id=str(li.id),
                line_number=li.line_number,
                description=li.description,
                quantity=li.quantity,
                unit_price_cents=li.unit_price_cents,
                received_quantity=li.received_quantity or 0,
            )
            for li in po_line_items
        ],
        created_at=po.created_at.isoformat() if po.created_at else "",
        updated_at=po.updated_at.isoformat() if po.updated_at else "",
    )
