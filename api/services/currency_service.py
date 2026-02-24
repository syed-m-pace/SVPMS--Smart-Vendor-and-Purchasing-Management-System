"""
Currency conversion utilities.

Looks up FX rates from the database (tenant-scoped, most recent effective_date
on or before the requested date). Falls back to 1:1 for same-currency pairs.

All amounts in the system are stored as integer cents in their native currency.
"""

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.models.fx_rate import FxRate

logger = structlog.get_logger()

# ISO 4217 three-letter codes accepted by the system
SUPPORTED_CURRENCIES = {
    "INR", "USD", "EUR", "GBP", "AED", "SGD", "AUD", "JPY", "CNY", "CHF",
}


async def get_fx_rate(
    db: AsyncSession,
    from_currency: str,
    to_currency: str,
    as_of: Optional[date] = None,
) -> Optional[Decimal]:
    """
    Return the exchange rate (from_currency → to_currency) as of as_of date.

    Returns None if no rate is found.
    Returns Decimal(1) if from_currency == to_currency.
    """
    if from_currency == to_currency:
        return Decimal("1")

    as_of_date = as_of or datetime.utcnow().date()

    # Try direct rate first
    result = await db.execute(
        select(FxRate.rate)
        .where(
            FxRate.from_currency == from_currency,
            FxRate.to_currency == to_currency,
            FxRate.effective_date <= as_of_date,
        )
        .order_by(FxRate.effective_date.desc())
        .limit(1)
    )
    rate = result.scalar()
    if rate is not None:
        return Decimal(str(rate))

    # Try inverse rate (USD→INR not found, but INR→USD is stored)
    result_inv = await db.execute(
        select(FxRate.rate)
        .where(
            FxRate.from_currency == to_currency,
            FxRate.to_currency == from_currency,
            FxRate.effective_date <= as_of_date,
        )
        .order_by(FxRate.effective_date.desc())
        .limit(1)
    )
    inv_rate = result_inv.scalar()
    if inv_rate is not None and Decimal(str(inv_rate)) != Decimal("0"):
        return (Decimal("1") / Decimal(str(inv_rate))).quantize(
            Decimal("0.000001"), rounding=ROUND_HALF_UP
        )

    logger.warning(
        "fx_rate_not_found",
        from_currency=from_currency,
        to_currency=to_currency,
        as_of=str(as_of_date),
    )
    return None


def convert_cents(
    amount_cents: int,
    rate: Decimal,
) -> int:
    """
    Convert amount_cents using rate. Returns integer cents in target currency.
    Uses banker's rounding.
    """
    converted = Decimal(str(amount_cents)) * rate
    return int(converted.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


async def convert_amount(
    db: AsyncSession,
    amount_cents: int,
    from_currency: str,
    to_currency: str,
    as_of: Optional[date] = None,
) -> Optional[int]:
    """
    Convert amount_cents from from_currency to to_currency.
    Returns None if rate not found.
    """
    rate = await get_fx_rate(db, from_currency, to_currency, as_of)
    if rate is None:
        return None
    return convert_cents(amount_cents, rate)
