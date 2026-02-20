from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.middleware.auth import get_current_user
from api.middleware.tenant import get_db_with_tenant
from api.middleware.authorization import require_roles
from api.models.rfq import Rfq, RfqLineItem, RfqBid
from api.models.vendor import Vendor
from api.models.user import User
from api.services.notification_service import send_notification
from api.services.push_service import send_push
from api.schemas.rfq import (
    RfqCreate,
    RfqResponse,
    RfqLineItemResponse,
    RfqBidCreate,
    RfqBidResponse,
)
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


async def _build_response(db: AsyncSession, rfq: Rfq) -> RfqResponse:
    lines_result = await db.execute(
        select(RfqLineItem).where(RfqLineItem.rfq_id == rfq.id)
    )
    bids_result = await db.execute(
        select(RfqBid).where(RfqBid.rfq_id == rfq.id).order_by(RfqBid.total_cents)
    )
    return RfqResponse(
        id=str(rfq.id),
        tenant_id=str(rfq.tenant_id),
        rfq_number=rfq.rfq_number,
        title=rfq.title,
        pr_id=str(rfq.pr_id) if rfq.pr_id else None,
        status=rfq.status,
        deadline=rfq.deadline.isoformat() if rfq.deadline else "",
        created_by=str(rfq.created_by),
        line_items=[_line_to_response(li) for li in lines_result.scalars().all()],
        bids=[_bid_to_response(b) for b in bids_result.scalars().all()],
        created_at=rfq.created_at.isoformat() if rfq.created_at else "",
    )


@router.get("", response_model=PaginatedResponse[RfqResponse])
async def list_rfqs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    rfq_status: str = Query(None, alias="status"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    q = select(Rfq)
    count_q = select(func.count(Rfq.id))

    if rfq_status:
        q = q.where(Rfq.status == rfq_status)
        count_q = count_q.where(Rfq.status == rfq_status)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        q.order_by(Rfq.created_at.desc()).offset((page - 1) * limit).limit(limit)
    )
    rfqs = result.scalars().all()

    items = []
    for rfq in rfqs:
        items.append(await _build_response(db, rfq))

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
    return await _build_response(db, rfq)


@router.post("", response_model=RfqResponse, status_code=status.HTTP_201_CREATED)
async def create_rfq(
    body: RfqCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("procurement", "procurement_lead", "admin")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    # Parse deadline
    try:
        deadline = datetime.fromisoformat(body.deadline)
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
                "notification", # fallback template if rfq_issued doesn't exist
                [vendor.email],
                {
                    "title": rfq.title,
                    "body": f"A new Request for Quotation ({rfq.rfq_number}) has been issued. Deadline: {rfq.deadline}",
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
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted a bid for this RFQ",
        )

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
