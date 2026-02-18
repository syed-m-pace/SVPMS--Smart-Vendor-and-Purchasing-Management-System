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
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    invoice_number: Mapped[str] = mapped_column(String(100), nullable=False)
    po_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id")
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), default="UPLOADED")
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date)
    total_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    document_url: Mapped[Optional[str]] = mapped_column(Text)
    ocr_status: Mapped[Optional[str]] = mapped_column(String(50))
    ocr_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    match_status: Mapped[Optional[str]] = mapped_column(String(50))
    match_exceptions: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "invoice_number",
            "vendor_id",
            name="uq_invoice_vendor",
        ),
        Index("idx_invoices_tenant", "tenant_id"),
        Index("idx_invoices_po", "po_id"),
        Index("idx_invoices_status", "status"),
    )


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "invoice_id", "line_number", name="uq_invoice_line_item"
        ),
        CheckConstraint("quantity > 0", name="chk_inv_line_qty"),
        CheckConstraint(
            "unit_price_cents > 0", name="chk_inv_line_price"
        ),
    )
