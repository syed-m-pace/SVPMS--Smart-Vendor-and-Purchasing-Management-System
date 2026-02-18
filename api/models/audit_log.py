import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Text, ForeignKey, Index, desc
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from api.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    actor_email: Mapped[Optional[str]] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    before_state: Mapped[Optional[dict]] = mapped_column(JSONB)
    after_state: Mapped[Optional[dict]] = mapped_column(JSONB)
    changed_fields: Mapped[Optional[list]] = mapped_column(
        ARRAY(Text)
    )
    ip_address = mapped_column(INET)
    user_agent: Mapped[Optional[str]] = mapped_column(Text)
    request_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    # Use "metadata" as the column name in DB, but "extra_metadata" as Python attr
    # to avoid conflict with SQLAlchemy's reserved .metadata attribute
    extra_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata", JSONB, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_audit_tenant", "tenant_id"),
        Index("idx_audit_entity", "entity_type", "entity_id"),
        Index("idx_audit_actor", "actor_id"),
        Index("idx_audit_created", desc("created_at")),
    )
