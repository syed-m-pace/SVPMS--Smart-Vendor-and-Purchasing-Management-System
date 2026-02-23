import secrets
import string
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.middleware.auth import get_current_user
from api.middleware.tenant import get_db_with_tenant
from api.middleware.authorization import require_roles
from api.models.vendor import Vendor
from api.models.purchase_order import PurchaseOrder
from api.models.audit_log import AuditLog
from api.models.user import User
from api.schemas.vendor import (
    VendorCreate,
    VendorUpdate,
    VendorResponse,
    VendorBlockRequest,
)
from api.schemas.common import PaginatedResponse, build_pagination
from api.services.audit_service import create_audit_log
from api.services.auth_service import hash_password
from api.services.email_service import send_email
from api.config import settings

logger = structlog.get_logger()
router = APIRouter()


def _generate_vendor_password() -> str:
    """Generate a secure random temporary password for new vendor accounts."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(16))
        # Ensure at least one of each required character class
        if (
            any(c.isupper() for c in pwd)
            and any(c.islower() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(c in "!@#$%^&*" for c in pwd)
        ):
            return pwd


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
        bank_account=v.bank_account_number_encrypted, # Exposing for profile view
        contact_person=v.phone, # Map phone as contact person for now
        created_at=v.created_at.isoformat() if v.created_at else "",
        updated_at=v.updated_at.isoformat() if v.updated_at else "",
    )


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


@router.get("", response_model=PaginatedResponse[VendorResponse])
async def list_vendors(
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=50),
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

    # Vendor users can only see their own vendor record(s).
    if current_user["role"] == "vendor":
        q = q.where(
            Vendor.tenant_id == current_user["tenant_id"],
            Vendor.email == current_user["email"],
        )
        count_q = count_q.where(
            Vendor.tenant_id == current_user["tenant_id"],
            Vendor.email == current_user["email"],
        )

    # Admins can see all non-draft vendors, but only their own draft vendors.
    if current_user["role"] == "admin":
        own_draft_vendor_ids = select(AuditLog.entity_id).where(
            AuditLog.entity_type == "VENDOR",
            AuditLog.action == "VENDOR_CREATED",
            AuditLog.actor_id == current_user["user_id"],
        )
        q = q.where(
            or_(
                Vendor.status != "DRAFT",
                Vendor.id.in_(own_draft_vendor_ids),
            )
        )
        count_q = count_q.where(
            or_(
                Vendor.status != "DRAFT",
                Vendor.id.in_(own_draft_vendor_ids),
            )
        )

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        q.order_by(Vendor.legal_name).offset((page - 1) * limit).limit(limit)
    )
    items = [_to_response(v) for v in result.scalars().all()]
    return PaginatedResponse(data=items, pagination=build_pagination(page, limit, total))


@router.get("/me", response_model=VendorResponse)
async def get_vendor_me(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    if current_user["role"] != "vendor":
        raise HTTPException(status_code=403, detail="Only vendor users can access this endpoint")

    vendor = await _resolve_vendor_for_user(db, current_user)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")

    return _to_response(vendor)


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

    if current_user["role"] == "vendor" and (
        str(vendor.tenant_id) != current_user["tenant_id"]
        or vendor.email != current_user["email"]
    ):
        raise HTTPException(status_code=404, detail="Vendor not found")

    return _to_response(vendor)


@router.post("", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    body: VendorCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("procurement", "procurement_lead", "admin", "manager")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    existing_tax = await db.execute(
        select(Vendor).where(Vendor.tax_id == body.tax_id, Vendor.deleted_at == None)  # noqa: E711
    )
    if existing_tax.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vendor with this tax_id already exists",
        )

    existing_vendor_email = await db.execute(
        select(Vendor).where(Vendor.email == body.email, Vendor.deleted_at == None)  # noqa: E711
    )
    if existing_vendor_email.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vendor with this email already exists",
        )

    existing_user_result = await db.execute(select(User).where(User.email == body.email))
    existing_user = existing_user_result.scalar_one_or_none()
    if existing_user:
        if existing_user.role != "vendor":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists for a non-vendor user",
            )
        if str(existing_user.tenant_id) != current_user["tenant_id"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists for a vendor in another tenant",
            )

    vendor = Vendor(
        tenant_id=current_user["tenant_id"],
        legal_name=body.legal_name,
        tax_id=body.tax_id,
        email=body.email,
        phone=body.phone,
        status="DRAFT",
        risk_score=0,
        rating=0,
        bank_name=body.bank_name,
        ifsc_code=body.ifsc_code,
        bank_account_number_encrypted=body.bank_account_number,
    )
    db.add(vendor)

    temp_password = _generate_vendor_password()
    if existing_user is None:
        user = User(
            tenant_id=current_user["tenant_id"],
            email=body.email,
            password_hash=hash_password(temp_password),
            first_name=body.legal_name,
            last_name="Vendor",
            role="vendor",
            is_active=True,
        )
        db.add(user)
    else:
        existing_user.is_active = True
        if not existing_user.password_hash:
            existing_user.password_hash = hash_password(temp_password)

    await db.flush()

    await create_audit_log(
        db,
        tenant_id=current_user["tenant_id"],
        actor_id=current_user["user_id"],
        action="VENDOR_CREATED",
        entity_type="VENDOR",
        entity_id=str(vendor.id),
        before_state=None,
        after_state={"status": vendor.status},
        actor_email=current_user.get("email"),
    )

    if existing_user is None:
        background_tasks.add_task(
            send_email,
            to_emails=[body.email],
            subject=f"Welcome to {settings.APP_NAME} — Your Vendor Account",
            html_content=(
                f"<h2>Welcome to {settings.APP_NAME}!</h2>"
                f"<p>Your vendor account has been created by our procurement team.</p>"
                f"<p><strong>Login Email:</strong> {body.email}<br>"
                f"<strong>Temporary Password:</strong> {temp_password}</p>"
                f"<p>Please log in and change your password immediately.</p>"
                f"<p>If you have any questions, contact your procurement point of contact.</p>"
            ),
        )

    return _to_response(vendor)


@router.patch("/{vendor_id}", response_model=VendorResponse)
async def update_vendor(
    vendor_id: str,
    body: VendorUpdate,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("procurement_lead", "admin", "manager")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(
        select(Vendor).where(Vendor.id == vendor_id, Vendor.deleted_at == None)  # noqa: E711
    )
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    for field, val in body.model_dump(exclude_unset=True).items():
        if field == "bank_account_number":
            vendor.bank_account_number_encrypted = val
        else:
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
    _auth: None = Depends(require_roles("manager", "procurement_lead", "admin")),
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
