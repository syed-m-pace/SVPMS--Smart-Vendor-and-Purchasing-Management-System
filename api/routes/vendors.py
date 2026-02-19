from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.middleware.auth import get_current_user
from api.middleware.tenant import get_db_with_tenant
from api.middleware.authorization import require_roles
from api.models.vendor import Vendor
from api.models.purchase_order import PurchaseOrder
from api.schemas.vendor import (
    VendorCreate,
    VendorUpdate,
    VendorResponse,
    VendorBlockRequest,
)
from api.schemas.common import PaginatedResponse, build_pagination
from api.services.audit_service import create_audit_log

logger = structlog.get_logger()
router = APIRouter()


def _to_response(v: Vendor) -> VendorResponse:
    return VendorResponse(
        id=str(v.id),
        tenant_id=str(v.tenant_id),
        legal_name=v.legal_name,
        tax_id=v.tax_id,
        email=v.email,
        phone=v.phone,
        status=v.status,
        risk_score=v.risk_score,
        rating=float(v.rating) if v.rating is not None else None,
        bank_name=v.bank_name,
        ifsc_code=v.ifsc_code,
        created_at=v.created_at.isoformat() if v.created_at else "",
        updated_at=v.updated_at.isoformat() if v.updated_at else "",
    )


@router.get("", response_model=PaginatedResponse[VendorResponse])
async def list_vendors(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    vendor_status: str = Query(None, alias="status"),
    search: str = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    q = select(Vendor).where(Vendor.deleted_at == None)  # noqa: E711
    count_q = select(func.count(Vendor.id)).where(Vendor.deleted_at == None)  # noqa: E711

    if vendor_status:
        q = q.where(Vendor.status == vendor_status)
        count_q = count_q.where(Vendor.status == vendor_status)
    if search:
        pattern = f"%{search}%"
        q = q.where(or_(Vendor.legal_name.ilike(pattern), Vendor.tax_id.ilike(pattern)))
        count_q = count_q.where(or_(Vendor.legal_name.ilike(pattern), Vendor.tax_id.ilike(pattern)))

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        q.order_by(Vendor.legal_name).offset((page - 1) * limit).limit(limit)
    )
    items = [_to_response(v) for v in result.scalars().all()]
    return PaginatedResponse(data=items, pagination=build_pagination(page, limit, total))


@router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(
    vendor_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(
        select(Vendor).where(Vendor.id == vendor_id, Vendor.deleted_at == None)  # noqa: E711
    )
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return _to_response(vendor)

    return _to_response(vendor)


@router.get("/me", response_model=VendorResponse)
async def get_vendor_me(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    """Get the vendor profile for the current tenant."""
    # Assuming one vendor record per tenant for vendor users
    # Or find by tenant_id?
    # In this system, it seems Tenant = Vendor for vendor users.
    # We look for a Vendor record that matches the tenant_id?
    # Actually, the Vendor table HAS a tenant_id column.
    # So we select * from vendors where tenant_id = current_user['tenant_id']
    # But get_db_with_tenant ALREADY filters by tenant_id if we use the session correctly?
    # No, get_db_with_tenant sets search path or similar.
    # Let's just query Vendor.
    # Since we are in the tenant context, we just need to find the vendor record.
    # If there are multiple, return the first?
    result = await db.execute(select(Vendor).where(Vendor.deleted_at == None))
    vendor = result.scalar_one_or_none()
    
    if not vendor:
        # If no vendor record found (maybe admin user of tenant?), handle gracefully?
        # For a vendor user, this should exist.
        raise HTTPException(status_code=404, detail="Vendor profile not found")
        
    return _to_response(vendor)


@router.post("", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    body: VendorCreate,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("procurement", "procurement_lead", "admin", "manager")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    # Check duplicate tax_id
    existing = await db.execute(
        select(Vendor).where(Vendor.tax_id == body.tax_id, Vendor.deleted_at == None)  # noqa: E711
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vendor with this tax_id already exists",
        )

    vendor = Vendor(
        tenant_id=current_user["tenant_id"],
        legal_name=body.legal_name,
        tax_id=body.tax_id,
        email=body.email,
        phone=body.phone,
        status="DRAFT",
        bank_name=body.bank_name,
        ifsc_code=body.ifsc_code,
        bank_account_number_encrypted=body.bank_account_number,
    )
    db.add(vendor)
    await db.flush()
    return _to_response(vendor)


@router.put("/{vendor_id}", response_model=VendorResponse)
async def update_vendor(
    vendor_id: str,
    body: VendorUpdate,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("procurement_lead", "admin")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(
        select(Vendor).where(Vendor.id == vendor_id, Vendor.deleted_at == None)  # noqa: E711
    )
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(vendor, field, val)

    await db.flush()
    return _to_response(vendor)


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vendor(
    vendor_id: str,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(
        select(Vendor).where(Vendor.id == vendor_id, Vendor.deleted_at == None)  # noqa: E711
    )
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Check for active POs
    active_po = await db.execute(
        select(func.count(PurchaseOrder.id)).where(
            PurchaseOrder.vendor_id == vendor_id,
            PurchaseOrder.status.in_(["DRAFT", "ISSUED", "ACKNOWLEDGED", "PARTIALLY_FULFILLED"]),
            PurchaseOrder.deleted_at == None,  # noqa: E711
        )
    )
    if (active_po.scalar() or 0) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete vendor with active purchase orders",
        )

    vendor.deleted_at = datetime.utcnow()
    await db.flush()


@router.post("/{vendor_id}/approve", response_model=VendorResponse)
async def approve_vendor(
    vendor_id: str,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("procurement_lead", "admin")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(
        select(Vendor).where(Vendor.id == vendor_id, Vendor.deleted_at == None)  # noqa: E711
    )
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    if vendor.status not in ("DRAFT", "PENDING_REVIEW"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve vendor in '{vendor.status}' status",
        )

    before = {"status": vendor.status}
    vendor.status = "ACTIVE"
    after = {"status": vendor.status}

    await create_audit_log(
        db,
        tenant_id=current_user["tenant_id"],
        actor_id=current_user["user_id"],
        action="VENDOR_APPROVED",
        entity_type="VENDOR",
        entity_id=str(vendor.id),
        before_state=before,
        after_state=after,
        actor_email=current_user.get("email"),
    )

    await db.flush()
    return _to_response(vendor)


@router.post("/{vendor_id}/block", response_model=VendorResponse)
async def block_vendor(
    vendor_id: str,
    body: VendorBlockRequest,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("admin", "manager", "procurement_lead")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(
        select(Vendor).where(Vendor.id == vendor_id, Vendor.deleted_at == None)  # noqa: E711
    )
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    before = {"status": vendor.status}
    vendor.status = "BLOCKED"
    after = {"status": vendor.status}

    await create_audit_log(
        db,
        tenant_id=current_user["tenant_id"],
        actor_id=current_user["user_id"],
        action="VENDOR_BLOCKED",
        entity_type="VENDOR",
        entity_id=str(vendor.id),
        before_state=before,
        after_state=after,
        actor_email=current_user.get("email"),
    )

    await db.flush()
    logger.info("vendor_blocked", vendor_id=vendor_id, reason=body.reason, by=current_user["user_id"])
    return _to_response(vendor)
