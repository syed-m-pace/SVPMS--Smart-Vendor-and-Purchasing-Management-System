"""
FX Rate model — stores daily exchange rates relative to a base currency (INR).

Each row: base_currency → quote_currency at a specific rate on a given date.
Tenants can manage their own FX rates or use system defaults.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class FxRate(Base):
    __tablename__ = "fx_rates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    # The currency being priced (e.g. "USD")
    from_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    # The reference currency (e.g. "INR")
    to_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    # Units of to_currency per 1 unit of from_currency (e.g. 83.50 for 1 USD = 83.50 INR)
    rate: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "from_currency", "to_currency", "effective_date",
            name="uq_fx_rate_tenant_pair_date",
        ),
        Index("idx_fx_rates_tenant", "tenant_id"),
        Index("idx_fx_rates_date", "effective_date"),
    )
