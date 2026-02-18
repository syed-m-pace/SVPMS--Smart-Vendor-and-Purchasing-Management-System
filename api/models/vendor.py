import uuid
from datetime import datetime
from typing import Optional
from decimal import Decimal

from sqlalchemy import (
    String,
    Integer,
    Numeric,
    DateTime,
    BigInteger,
    Date,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    legal_name: Mapped[str] = mapped_column(String(200), nullable=False)
    tax_id: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(50), default="DRAFT")
    risk_score: Mapped[Optional[int]] = mapped_column(Integer)
    rating: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))
    bank_account_number_encrypted: Mapped[Optional[str]] = mapped_column(Text)
    bank_name: Mapped[Optional[str]] = mapped_column(String(200))
    ifsc_code: Mapped[Optional[str]] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    __table_args__ = (
        Index("idx_vendors_tenant", "tenant_id"),
        Index("idx_vendors_status", "status"),
        Index("idx_vendors_email", "email"),
    )


class VendorDocument(Base):
    __tablename__ = "vendor_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    file_name: Mapped[Optional[str]] = mapped_column(String(255))
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
    expiry_date: Mapped[Optional[datetime]] = mapped_column(Date)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_vdocs_vendor", "vendor_id"),
    )
