"""
Contract management — /api/v1/contracts

CRUD for vendor contracts with lifecycle management:
  DRAFT → ACTIVE → EXPIRED / TERMINATED
"""

import uuid
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.middleware.auth import get_current_user
from api.middleware.tenant import get_db_with_tenant
from api.middleware.authorization import require_roles
from api.models.contract import Contract
from api.models.vendor import Vendor
from api.schemas.common import PaginatedResponse, build_pagination
from api.services.audit_service import create_audit_log
from api.services.notification_service import send_notification

logger = structlog.get_logger()
router = APIRouter()

_PRIVILEGED_ROLES = {
    "admin", "finance_head", "cfo", "procurement", "procurement_lead", "finance", "manager"
}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ContractCreate(BaseModel):
    vendor_id: str
    po_id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    value_cents: Optional[int] = Field(None, ge=0)
    currency: str = Field("INR", min_length=3, max_length=3)
    start_date: date
    end_date: date
    auto_renew: bool = False
    renewal_notice_days: int = Field(30, ge=1, le=365)
    sla_terms: Optional[str] = None


class ContractUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    value_cents: Optional[int] = Field(None, ge=0)
    end_date: Optional[date] = None
    auto_renew: Optional[bool] = None
    renewal_notice_days: Optional[int] = Field(None, ge=1, le=365)
    sla_terms: Optional[str] = None


class ContractResponse(BaseModel):
    id: str
    contract_number: str
    vendor_id: str
    vendor_name: Optional[str] = None
    po_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    status: str
    value_cents: Optional[int] = None
    currency: str
    start_date: str
    end_date: str
    auto_renew: bool
    renewal_notice_days: int
    sla_terms: Optional[str] = None
    document_key: Optional[str] = None
    terminated_at: Optional[str] = None
    created_at: str

    model_config = {"from_attributes": True}


def _to_response(c: Contract, vendor_name: Optional[str] = None) -> ContractResponse:
    return ContractResponse(
        id=str(c.id),
        contract_number=c.contract_number,
        vendor_id=str(c.vendor_id),
        vendor_name=vendor_name,
        po_id=str(c.po_id) if c.po_id else None,
        title=c.title,
        description=c.description,
        status=c.status,
        value_cents=c.value_cents,
        currency=c.currency,
        start_date=str(c.start_date),
        end_date=str(c.end_date),
        auto_renew=c.auto_renew,
        renewal_notice_days=c.renewal_notice_days,
        sla_terms=c.sla_terms,
        document_key=c.document_key,
        terminated_at=c.terminated_at.isoformat() if c.terminated_at else None,
        created_at=c.created_at.isoformat(),
    )


def _generate_contract_number() -> str:
    return f"CNT-{datetime.utcnow().strftime('%Y%m')}-{str(uuid.uuid4())[:6].upper()}"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=PaginatedResponse[ContractResponse])
async def list_contracts(
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=25),
    vendor_id: Optional[str] = Query(None),
    contract_status: Optional[str] = Query(None, alias="status"),
    expiring_within_days: Optional[int] = Query(None, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    """List contracts. Supports filtering by vendor, status, and upcoming expiry."""
    q = (
        select(Contract, Vendor.legal_name)
        .join(Vendor, Contract.vendor_id == Vendor.id, isouter=True)
        .where(Contract.deleted_at.is_(None))
    )
    count_q = select(func.count(Contract.id)).where(Contract.deleted_at.is_(None))

    if vendor_id:
        q = q.where(Contract.vendor_id == vendor_id)
        count_q = count_q.where(Contract.vendor_id == vendor_id)
    if contract_status:
        q = q.where(Contract.status == contract_status.upper())
        count_q = count_q.where(Contract.status == contract_status.upper())
    if expiring_within_days:
        cutoff = datetime.utcnow().date()
        expiry = datetime.utcnow().date()
        from datetime import timedelta
        expiry_limit = expiry.__class__.today() + expiry.__class__.resolution * expiring_within_days
        q = q.where(
            Contract.end_date >= datetime.utcnow().date(),
            Contract.end_date <= datetime.utcnow().date().__class__.fromordinal(
                datetime.utcnow().date().toordinal() + expiring_within_days
            ),
            Contract.status == "ACTIVE",
        )
        count_q = count_q.where(
            Contract.end_date >= datetime.utcnow().date(),
            Contract.end_date <= datetime.utcnow().date().__class__.fromordinal(
                datetime.utcnow().date().toordinal() + expiring_within_days
            ),
            Contract.status == "ACTIVE",
        )

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        q.order_by(Contract.end_date.asc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    rows = result.all()
    items = [_to_response(row[0], row[1]) for row in rows]
    return PaginatedResponse(data=items, pagination=build_pagination(page, limit, total))


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(
        select(Contract, Vendor.legal_name)
        .join(Vendor, Contract.vendor_id == Vendor.id, isouter=True)
        .where(Contract.id == contract_id, Contract.deleted_at.is_(None))
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Contract not found")
    return _to_response(row[0], row[1])


@router.post("", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
async def create_contract(
    body: ContractCreate,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(
        require_roles("admin", "procurement_lead", "procurement", "finance_head", "cfo")
    ),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    if body.end_date <= body.start_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")

    vendor_result = await db.execute(
        select(Vendor).where(Vendor.id == body.vendor_id, Vendor.deleted_at.is_(None))
    )
    vendor = vendor_result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    contract = Contract(
        tenant_id=current_user["tenant_id"],
        contract_number=_generate_contract_number(),
        vendor_id=body.vendor_id,
        po_id=body.po_id,
        title=body.title,
        description=body.description,
        status="DRAFT",
        value_cents=body.value_cents,
        currency=body.currency.upper(),
        start_date=body.start_date,
        end_date=body.end_date,
        auto_renew=body.auto_renew,
        renewal_notice_days=body.renewal_notice_days,
        sla_terms=body.sla_terms,
        created_by=current_user["user_id"],
    )
    db.add(contract)
    await db.flush()
    await db.refresh(contract)

    await create_audit_log(
        db,
        tenant_id=current_user["tenant_id"],
        actor_id=current_user["user_id"],
        action="CONTRACT_CREATED",
        entity_type="CONTRACT",
        entity_id=str(contract.id),
        before_state=None,
        after_state={"status": contract.status, "vendor_id": str(contract.vendor_id)},
        actor_email=current_user.get("email"),
    )

    return _to_response(contract, vendor.legal_name)


@router.patch("/{contract_id}", response_model=ContractResponse)
async def update_contract(
    contract_id: str,
    body: ContractUpdate,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(
        require_roles("admin", "procurement_lead", "finance_head", "cfo")
    ),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(
        select(Contract, Vendor.legal_name)
        .join(Vendor, Contract.vendor_id == Vendor.id, isouter=True)
        .where(Contract.id == contract_id, Contract.deleted_at.is_(None))
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Contract not found")
    contract, vendor_name = row

    if contract.status == "TERMINATED":
        raise HTTPException(status_code=400, detail="Cannot modify a terminated contract")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(contract, field, value)

    if body.end_date and body.end_date <= contract.start_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")

    await db.flush()
    await db.refresh(contract)
    return _to_response(contract, vendor_name)


@router.post("/{contract_id}/activate", response_model=ContractResponse)
async def activate_contract(
    contract_id: str,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(
        require_roles("admin", "procurement_lead", "finance_head", "cfo")
    ),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    """Transition contract DRAFT → ACTIVE."""
    result = await db.execute(
        select(Contract, Vendor.legal_name)
        .join(Vendor, Contract.vendor_id == Vendor.id, isouter=True)
        .where(Contract.id == contract_id, Contract.deleted_at.is_(None))
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Contract not found")
    contract, vendor_name = row

    if contract.status != "DRAFT":
        raise HTTPException(
            status_code=400, detail=f"Cannot activate contract in '{contract.status}' status"
        )

    before = {"status": contract.status}
    contract.status = "ACTIVE"
    await db.flush()

    await create_audit_log(
        db,
        tenant_id=current_user["tenant_id"],
        actor_id=current_user["user_id"],
        action="CONTRACT_ACTIVATED",
        entity_type="CONTRACT",
        entity_id=str(contract.id),
        before_state=before,
        after_state={"status": contract.status},
        actor_email=current_user.get("email"),
    )

    return _to_response(contract, vendor_name)


@router.post("/{contract_id}/terminate", response_model=ContractResponse)
async def terminate_contract(
    contract_id: str,
    body: dict,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("admin", "finance_head", "cfo")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    """Terminate an ACTIVE contract."""
    result = await db.execute(
        select(Contract, Vendor.legal_name)
        .join(Vendor, Contract.vendor_id == Vendor.id, isouter=True)
        .where(Contract.id == contract_id, Contract.deleted_at.is_(None))
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Contract not found")
    contract, vendor_name = row

    if contract.status != "ACTIVE":
        raise HTTPException(
            status_code=400, detail=f"Cannot terminate contract in '{contract.status}' status"
        )

    reason = body.get("reason", "")
    if len(reason) < 10:
        raise HTTPException(status_code=400, detail="Termination reason must be at least 10 characters")

    before = {"status": contract.status}
    contract.status = "TERMINATED"
    contract.terminated_at = datetime.utcnow()
    contract.termination_reason = reason
    await db.flush()

    await create_audit_log(
        db,
        tenant_id=current_user["tenant_id"],
        actor_id=current_user["user_id"],
        action="CONTRACT_TERMINATED",
        entity_type="CONTRACT",
        entity_id=str(contract.id),
        before_state=before,
        after_state={"status": contract.status, "reason": reason},
        actor_email=current_user.get("email"),
    )

    return _to_response(contract, vendor_name)


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contract(
    contract_id: str,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    """Soft-delete a DRAFT contract."""
    result = await db.execute(
        select(Contract).where(Contract.id == contract_id, Contract.deleted_at.is_(None))
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    if contract.status != "DRAFT":
        raise HTTPException(
            status_code=400, detail="Only DRAFT contracts can be deleted"
        )
    contract.deleted_at = datetime.utcnow()
    await db.flush()
