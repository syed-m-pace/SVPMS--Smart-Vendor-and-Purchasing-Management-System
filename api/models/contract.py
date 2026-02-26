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
    # Changed to nullable=True to support Master Contracts that are not assigned to a vendor yet.
    # Legacy data will remain, but going forward this column might be empty for standard PDFs.
    vendor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True
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


class ContractVendor(Base):
    """
    Association table mapping Master Contracts to multiple Vendors.
    """
    __tablename__ = "contract_vendors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE")
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_contract_vendors_tenant", "tenant_id"),
        Index("idx_contract_vendors_contract", "contract_id"),
        Index("idx_contract_vendors_vendor", "vendor_id"),
    )
