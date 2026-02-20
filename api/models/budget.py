import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String,
    BigInteger,
    Integer,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    department_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id"), nullable=False
    )
    department: Mapped["Department"] = relationship("Department")
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    quarter: Mapped[int] = mapped_column(Integer, nullable=False)
    total_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    spent_cents: Mapped[int] = mapped_column(BigInteger, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "department_id",
            "fiscal_year",
            "quarter",
            name="uq_budget_tenant_dept_year_quarter",
        ),
        CheckConstraint("quarter IN (1,2,3,4)", name="chk_budget_quarter"),
        CheckConstraint("total_cents > 0", name="chk_budget_positive"),
        CheckConstraint(
            "spent_cents <= total_cents", name="chk_budget_spent"
        ),
        Index("idx_budgets_dept", "department_id", "fiscal_year"),
    )


class BudgetReservation(Base):
    __tablename__ = "budget_reservations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    budget_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budgets.id"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="COMMITTED")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    __table_args__ = (
        UniqueConstraint(
            "entity_type", "entity_id", name="uq_budget_res_entity"
        ),
        CheckConstraint(
            "entity_type IN ('PR', 'PO', 'INVOICE')",
            name="chk_budget_res_entity_type",
        ),
        CheckConstraint(
            "amount_cents > 0", name="chk_budget_res_amount_positive"
        ),
        CheckConstraint(
            "status IN ('COMMITTED', 'SPENT', 'RELEASED')",
            name="chk_budget_res_status",
        ),
        Index("idx_budget_res_budget", "budget_id", "status"),
        Index("idx_budget_res_entity", "entity_type", "entity_id"),
    )
