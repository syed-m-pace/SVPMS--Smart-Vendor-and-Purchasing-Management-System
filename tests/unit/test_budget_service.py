"""
Unit tests for api/services/budget_service.py

Uses AsyncMock to isolate from database — no Neon connection required.
Tests: check_budget_availability, reserve_budget,
       release_budget_reservation, commit_budget_spent,
       get_current_fiscal_period.
"""

import uuid
from typing import Optional
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.services.budget_service import (
    BudgetCheckResult,
    check_budget_availability,
    commit_budget_spent,
    get_current_fiscal_period,
    release_budget_reservation,
    reserve_budget,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_budget(
    total_cents: int = 10_000_00,
    spent_cents: int = 0,
    budget_id: Optional[str] = None,
    dept_id: Optional[str] = None,
):
    b = MagicMock()
    b.id = uuid.UUID(budget_id or str(uuid.uuid4()))
    b.department_id = dept_id or str(uuid.uuid4())
    b.total_cents = total_cents
    b.spent_cents = spent_cents
    return b


def _make_reservation(
    amount_cents: int = 5_000_00,
    status: str = "COMMITTED",
    budget_id: Optional[str] = None,
    res_id: Optional[str] = None,
):
    r = MagicMock()
    r.id = uuid.UUID(res_id or str(uuid.uuid4()))
    r.budget_id = uuid.UUID(budget_id or str(uuid.uuid4()))
    r.amount_cents = amount_cents
    r.status = status
    r.released_at = None
    return r


def _mock_session() -> AsyncMock:
    session = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


def _execute_result(scalar_value):
    """Return an execute() mock whose .scalar() returns scalar_value."""
    result = MagicMock()
    result.scalar.return_value = scalar_value
    result.scalar_one_or_none.return_value = scalar_value
    return result


# ---------------------------------------------------------------------------
# get_current_fiscal_period
# ---------------------------------------------------------------------------


def test_fiscal_period_q1():
    with patch("api.services.budget_service.datetime") as mock_dt:
        mock_dt.utcnow.return_value = datetime(2026, 1, 15)
        fy, q = get_current_fiscal_period()
    assert fy == 2026
    assert q == 1


def test_fiscal_period_q4():
    with patch("api.services.budget_service.datetime") as mock_dt:
        mock_dt.utcnow.return_value = datetime(2025, 12, 1)
        fy, q = get_current_fiscal_period()
    assert fy == 2025
    assert q == 4


def test_fiscal_period_boundary_month():
    """Month 3 → Q1, month 4 → Q2."""
    with patch("api.services.budget_service.datetime") as mock_dt:
        mock_dt.utcnow.return_value = datetime(2026, 3, 31)
        _, q = get_current_fiscal_period()
    assert q == 1

    with patch("api.services.budget_service.datetime") as mock_dt:
        mock_dt.utcnow.return_value = datetime(2026, 4, 1)
        _, q = get_current_fiscal_period()
    assert q == 2


# ---------------------------------------------------------------------------
# check_budget_availability
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_availability_no_budget():
    """Returns BUDGET_NOT_FOUND when no matching budget row exists."""
    session = _mock_session()
    # scalar_one_or_none returns None → budget not found
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    session.execute.return_value = result_mock

    result = await check_budget_availability(
        session=session,
        department_id=str(uuid.uuid4()),
        amount_cents=100_00,
        fiscal_year=2026,
        quarter=1,
    )

    assert result.success is False
    assert result.error_code == "BUDGET_NOT_FOUND"
    assert result.available_cents == 0


@pytest.mark.asyncio
async def test_check_availability_sufficient():
    """Returns success when budget minus reservations covers the request."""
    budget = _make_budget(total_cents=1_000_00, spent_cents=200_00)
    session = _mock_session()

    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        r = MagicMock()
        if call_count == 1:
            # First execute: budget SELECT FOR UPDATE
            r.scalar_one_or_none.return_value = budget
        else:
            # Second execute: SUM of COMMITTED reservations
            r.scalar.return_value = 100_00  # 100 reserved
        return r

    session.execute.side_effect = side_effect

    # available = 1000 - 200 - 100 = 700; requesting 300 → ok
    result = await check_budget_availability(
        session=session,
        department_id=str(budget.department_id),
        amount_cents=300_00,
        fiscal_year=2026,
        quarter=1,
    )

    assert result.success is True
    assert result.available_cents == 700_00
    assert result.budget_id == str(budget.id)


@pytest.mark.asyncio
async def test_check_availability_insufficient():
    """Returns BUDGET_EXCEEDED when available < requested."""
    budget = _make_budget(total_cents=500_00, spent_cents=0)
    session = _mock_session()
    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        r = MagicMock()
        if call_count == 1:
            r.scalar_one_or_none.return_value = budget
        else:
            r.scalar.return_value = 300_00  # 300 already reserved
        return r

    session.execute.side_effect = side_effect

    # available = 500 - 0 - 300 = 200; requesting 250 → fail
    result = await check_budget_availability(
        session=session,
        department_id=str(budget.department_id),
        amount_cents=250_00,
        fiscal_year=2026,
        quarter=1,
    )

    assert result.success is False
    assert result.error_code == "BUDGET_EXCEEDED"
    assert result.available_cents == 200_00
    assert result.requested_cents == 250_00


@pytest.mark.asyncio
async def test_check_availability_no_reservations():
    """Coalesce of empty reservation table returns 0 correctly."""
    budget = _make_budget(total_cents=1_000_00, spent_cents=0)
    session = _mock_session()
    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        r = MagicMock()
        if call_count == 1:
            r.scalar_one_or_none.return_value = budget
        else:
            r.scalar.return_value = None  # coalesce returns None when no rows
        return r

    session.execute.side_effect = side_effect

    result = await check_budget_availability(
        session=session,
        department_id=str(budget.department_id),
        amount_cents=500_00,
        fiscal_year=2026,
        quarter=1,
    )

    assert result.success is True
    assert result.available_cents == 1_000_00


# ---------------------------------------------------------------------------
# reserve_budget
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reserve_budget_creates_reservation():
    session = _mock_session()
    tenant_id = str(uuid.uuid4())
    budget_id = str(uuid.uuid4())
    entity_id = str(uuid.uuid4())

    reservation = await reserve_budget(
        session=session,
        budget_id=budget_id,
        entity_type="PURCHASE_REQUEST",
        entity_id=entity_id,
        amount_cents=500_00,
        tenant_id=tenant_id,
    )

    session.add.assert_called_once()
    session.flush.assert_awaited_once()
    assert reservation.status == "COMMITTED"
    assert reservation.amount_cents == 500_00
    assert str(reservation.budget_id) == budget_id


# ---------------------------------------------------------------------------
# release_budget_reservation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_release_reservation_found():
    reservation = _make_reservation(amount_cents=200_00, status="COMMITTED")
    session = _mock_session()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = reservation
    session.execute.return_value = result_mock

    released = await release_budget_reservation(
        session=session,
        entity_type="PURCHASE_REQUEST",
        entity_id=str(uuid.uuid4()),
    )

    assert released is True
    assert reservation.status == "RELEASED"
    assert reservation.released_at is not None
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_release_reservation_not_found():
    session = _mock_session()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    session.execute.return_value = result_mock

    released = await release_budget_reservation(
        session=session,
        entity_type="PURCHASE_REQUEST",
        entity_id=str(uuid.uuid4()),
    )

    assert released is False
    session.flush.assert_not_awaited()


# ---------------------------------------------------------------------------
# commit_budget_spent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_commit_budget_spent_increments_spent_cents():
    budget = _make_budget(total_cents=1_000_00, spent_cents=0)
    reservation = _make_reservation(
        amount_cents=300_00,
        status="COMMITTED",
        budget_id=str(budget.id),
    )
    session = _mock_session()
    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        r = MagicMock()
        if call_count == 1:
            r.scalar_one_or_none.return_value = reservation
        else:
            r.scalar_one_or_none.return_value = budget
        return r

    session.execute.side_effect = side_effect

    result = await commit_budget_spent(
        session=session,
        entity_type="PURCHASE_ORDER",
        entity_id=str(uuid.uuid4()),
    )

    assert result is True
    assert reservation.status == "SPENT"
    assert budget.spent_cents == 300_00  # was 0, now incremented
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_commit_budget_spent_no_reservation():
    session = _mock_session()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    session.execute.return_value = result_mock

    result = await commit_budget_spent(
        session=session,
        entity_type="PURCHASE_ORDER",
        entity_id=str(uuid.uuid4()),
    )

    assert result is False
