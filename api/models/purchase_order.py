import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    String,
    BigInteger,
    Integer,
    DateTime,
    Date,
    Text,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    po_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )
    pr_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_requests.id")
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), default="DRAFT")
    total_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    expected_delivery_date: Mapped[Optional[date]] = mapped_column(Date)
    terms_and_conditions: Mapped[Optional[str]] = mapped_column(Text)
    issued_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    __table_args__ = (
        Index("idx_po_tenant", "tenant_id"),
        Index("idx_po_vendor", "vendor_id"),
        Index("idx_po_status", "status"),
    )


class PoLineItem(Base):
    __tablename__ = "po_line_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    po_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    received_quantity: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("po_id", "line_number", name="uq_po_line_item"),
        CheckConstraint("quantity > 0", name="chk_po_line_qty"),
        CheckConstraint(
            "unit_price_cents > 0", name="chk_po_line_price"
        ),
        Index("idx_po_items_po", "po_id"),
    )
