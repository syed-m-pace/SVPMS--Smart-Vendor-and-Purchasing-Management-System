"""
Budget service — pessimistic locking, reservation management.

All functions use the caller's session (no commit). get_db() auto-commits.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.models.budget import Budget, BudgetReservation

logger = structlog.get_logger()


@dataclass
class BudgetCheckResult:
    success: bool
    available_cents: int
    requested_cents: int
    budget_id: Optional[str] = None
    error_code: Optional[str] = None
    message: Optional[str] = None


def get_current_fiscal_period() -> tuple[int, int]:
    """Returns (fiscal_year, quarter) from current UTC date."""
    now = datetime.utcnow()
    quarter = (now.month - 1) // 3 + 1
    return now.year, quarter


async def check_budget_availability(
    session: AsyncSession,
    department_id: str,
    amount_cents: int,
    fiscal_year: int,
    quarter: int,
) -> BudgetCheckResult:
    """
    SELECT FOR UPDATE on budget row, sum COMMITTED reservations,
    return availability check result.
    """
    # Lock the budget row
    result = await session.execute(
        select(Budget)
        .where(
            Budget.department_id == department_id,
            Budget.fiscal_year == fiscal_year,
            Budget.quarter == quarter,
        )
        .with_for_update()
    )
    budget = result.scalar_one_or_none()

    if not budget:
        return BudgetCheckResult(
            success=False,
            available_cents=0,
            requested_cents=amount_cents,
            error_code="BUDGET_NOT_FOUND",
            message=f"No budget found for department in {fiscal_year} Q{quarter}",
        )

    # Sum all COMMITTED reservations against this budget
    reserved_result = await session.execute(
        select(func.coalesce(func.sum(BudgetReservation.amount_cents), 0)).where(
            BudgetReservation.budget_id == budget.id,
            BudgetReservation.status == "COMMITTED",
        )
    )
    reserved_cents = int(reserved_result.scalar() or 0)

    available_cents = budget.total_cents - budget.spent_cents - reserved_cents

    if amount_cents > available_cents:
        return BudgetCheckResult(
            success=False,
            available_cents=available_cents,
            requested_cents=amount_cents,
            budget_id=str(budget.id),
            error_code="BUDGET_EXCEEDED",
            message=(
                f"Insufficient budget: requested {amount_cents} cents, "
                f"available {available_cents} cents"
            ),
        )

    return BudgetCheckResult(
        success=True,
        available_cents=available_cents,
        requested_cents=amount_cents,
        budget_id=str(budget.id),
    )


async def reserve_budget(
    session: AsyncSession,
    budget_id: str,
    entity_type: str,
    entity_id: str,
    amount_cents: int,
    tenant_id: str,
) -> BudgetReservation:
    """Create a COMMITTED budget reservation."""
    reservation = BudgetReservation(
        tenant_id=tenant_id,
        budget_id=budget_id,
        entity_type=entity_type,
        entity_id=entity_id,
        amount_cents=amount_cents,
        status="COMMITTED",
    )
    session.add(reservation)
    await session.flush()

    logger.info(
        "budget_reserved",
        budget_id=budget_id,
        entity_type=entity_type,
        entity_id=entity_id,
        amount_cents=amount_cents,
    )
    return reservation


async def release_budget_reservation(
    session: AsyncSession,
    entity_type: str,
    entity_id: str,
) -> bool:
    """Release a COMMITTED reservation (sets status=RELEASED)."""
    result = await session.execute(
        select(BudgetReservation).where(
            BudgetReservation.entity_type == entity_type,
            BudgetReservation.entity_id == entity_id,
            BudgetReservation.status == "COMMITTED",
        )
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        logger.warning(
            "budget_reservation_not_found",
            entity_type=entity_type,
            entity_id=entity_id,
        )
        return False

    reservation.status = "RELEASED"
    reservation.released_at = datetime.utcnow()
    await session.flush()

    logger.info(
        "budget_released",
        entity_type=entity_type,
        entity_id=entity_id,
    )
    return True


async def commit_budget_spent(
    session: AsyncSession,
    entity_type: str,
    entity_id: str,
) -> bool:
    """Move reservation COMMITTED→SPENT and increment budget.spent_cents."""
    result = await session.execute(
        select(BudgetReservation).where(
            BudgetReservation.entity_type == entity_type,
            BudgetReservation.entity_id == entity_id,
            BudgetReservation.status == "COMMITTED",
        )
    )
    reservation = result.scalar_one_or_none()
    if not reservation:
        return False

    reservation.status = "SPENT"
    reservation.released_at = datetime.utcnow()

    # Increment spent_cents on the budget
    budget_result = await session.execute(
        select(Budget).where(Budget.id == reservation.budget_id).with_for_update()
    )
    budget = budget_result.scalar_one_or_none()
    if budget:
        budget.spent_cents += reservation.amount_cents

    await session.flush()

    logger.info(
        "budget_committed_spent",
        entity_type=entity_type,
        entity_id=entity_id,
        amount_cents=reservation.amount_cents,
    )
    return True
