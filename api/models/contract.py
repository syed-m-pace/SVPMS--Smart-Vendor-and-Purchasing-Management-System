"""
Contract model — legal agreements with vendors.

State machine: DRAFT → ACTIVE → EXPIRED / TERMINATED
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    contract_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False
    )
    # Optionally link to a PO that originated this contract
    po_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT")
    # Contract value
    value_cents: Mapped[Optional[int]] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    # Contract period
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Auto-renewal
    auto_renew: Mapped[bool] = mapped_column(default=False)
    renewal_notice_days: Mapped[int] = mapped_column(default=30)
    # Document storage key (Cloudflare R2)
    document_key: Mapped[Optional[str]] = mapped_column(String(255))
    # SLA fields
    sla_terms: Mapped[Optional[str]] = mapped_column(Text)
    # Termination tracking
    terminated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    termination_reason: Mapped[Optional[str]] = mapped_column(Text)
    # Created by user
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    __table_args__ = (
        Index("idx_contracts_tenant", "tenant_id"),
        Index("idx_contracts_vendor", "vendor_id"),
        Index("idx_contracts_status", "status"),
        Index("idx_contracts_end_date", "end_date"),
    )
