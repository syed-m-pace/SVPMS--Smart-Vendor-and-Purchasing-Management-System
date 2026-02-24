"""
FX Rate management — /api/v1/fx-rates

Finance and admin users manage exchange rates used for multi-currency conversions.
Vendors and read-only users can query rates.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.auth import get_current_user
from api.middleware.tenant import get_db_with_tenant
from api.middleware.authorization import require_roles
from api.models.fx_rate import FxRate
from api.services.currency_service import SUPPORTED_CURRENCIES, get_fx_rate

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class FxRateCreate(BaseModel):
    from_currency: str = Field(..., min_length=3, max_length=3)
    to_currency: str = Field(..., min_length=3, max_length=3)
    rate: float = Field(..., gt=0)
    effective_date: date

    @field_validator("from_currency", "to_currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        v = v.upper()
        if v not in SUPPORTED_CURRENCIES:
            raise ValueError(
                f"Unsupported currency '{v}'. Supported: {sorted(SUPPORTED_CURRENCIES)}"
            )
        return v

    @field_validator("rate")
    @classmethod
    def validate_rate(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Rate must be positive")
        return round(v, 6)


class FxRateResponse(BaseModel):
    id: str
    from_currency: str
    to_currency: str
    rate: float
    effective_date: str
    created_at: str

    model_config = {"from_attributes": True}


def _to_response(r: FxRate) -> FxRateResponse:
    return FxRateResponse(
        id=str(r.id),
        from_currency=r.from_currency,
        to_currency=r.to_currency,
        rate=float(r.rate),
        effective_date=str(r.effective_date),
        created_at=r.created_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("")
async def list_fx_rates(
    from_currency: Optional[str] = Query(None),
    to_currency: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    """List stored FX rates for the tenant, newest first."""
    q = (
        select(FxRate)
        .where(FxRate.tenant_id == current_user["tenant_id"])
        .order_by(FxRate.effective_date.desc(), FxRate.from_currency)
        .limit(200)
    )
    if from_currency:
        q = q.where(FxRate.from_currency == from_currency.upper())
    if to_currency:
        q = q.where(FxRate.to_currency == to_currency.upper())

    result = await db.execute(q)
    return [_to_response(r) for r in result.scalars().all()]


@router.post("", status_code=http_status.HTTP_201_CREATED)
async def create_or_update_fx_rate(
    body: FxRateCreate,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(
        require_roles("admin", "finance", "finance_head", "cfo")
    ),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    """
    Create or update an FX rate for a currency pair on a given date.
    Upserts: if a rate already exists for (from, to, date), it is updated.
    """
    if body.from_currency == body.to_currency:
        raise HTTPException(
            status_code=400, detail="from_currency and to_currency must differ"
        )

    existing = await db.execute(
        select(FxRate).where(
            FxRate.tenant_id == current_user["tenant_id"],
            FxRate.from_currency == body.from_currency,
            FxRate.to_currency == body.to_currency,
            FxRate.effective_date == body.effective_date,
        )
    )
    fx = existing.scalar_one_or_none()

    if fx:
        fx.rate = Decimal(str(body.rate))
        fx.updated_at = datetime.utcnow()
    else:
        fx = FxRate(
            tenant_id=current_user["tenant_id"],
            from_currency=body.from_currency,
            to_currency=body.to_currency,
            rate=Decimal(str(body.rate)),
            effective_date=body.effective_date,
            created_by=current_user["user_id"],
        )
        db.add(fx)

    await db.flush()
    await db.refresh(fx)
    return _to_response(fx)


@router.get("/convert")
async def convert_currency(
    amount: float = Query(..., gt=0, description="Amount in from_currency"),
    from_currency: str = Query(..., min_length=3, max_length=3),
    to_currency: str = Query(..., min_length=3, max_length=3),
    as_of: Optional[date] = Query(None, description="Rate date (defaults to today)"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    """Convert an amount between currencies using stored FX rates."""
    from_c = from_currency.upper()
    to_c = to_currency.upper()

    rate = await get_fx_rate(db, from_c, to_c, as_of)
    if rate is None:
        raise HTTPException(
            status_code=404,
            detail=f"No FX rate found for {from_c}→{to_c}. "
            "Add rates via POST /api/v1/fx-rates.",
        )

    converted = float(Decimal(str(amount)) * rate)
    return {
        "from_currency": from_c,
        "to_currency": to_c,
        "original_amount": amount,
        "converted_amount": round(converted, 4),
        "rate": float(rate),
        "as_of": str(as_of or datetime.utcnow().date()),
    }


@router.delete("/{rate_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_fx_rate(
    rate_id: str,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("admin", "finance_head")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    """Delete a specific FX rate entry."""
    result = await db.execute(
        select(FxRate).where(
            FxRate.id == rate_id,
            FxRate.tenant_id == current_user["tenant_id"],
        )
    )
    fx = result.scalar_one_or_none()
    if not fx:
        raise HTTPException(status_code=404, detail="FX rate not found")

    await db.delete(fx)
    await db.flush()
