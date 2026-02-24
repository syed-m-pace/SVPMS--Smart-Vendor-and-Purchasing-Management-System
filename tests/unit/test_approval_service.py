"""
Unit tests for api/services/approval_service.py

Tests: get_approval_chain (threshold routing), create_approval_workflow,
       process_approval (approve, reject, wrong approver, no pending step).
"""

import uuid
from datetime import datetime
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from api.services.approval_service import (
    THRESHOLD_CFO,
    THRESHOLD_FINANCE_HEAD,
    ApprovalResult,
    process_approval,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(role: str = "manager", user_id: Optional[str] = None):
    u = MagicMock()
    u.id = uuid.UUID(user_id or str(uuid.uuid4()))
    u.email = f"{role}@acme.com"
    u.role = role
    u.is_active = True
    return u


def _make_dept(manager_id: Optional[str] = None):
    d = MagicMock()
    d.id = uuid.UUID(str(uuid.uuid4()))
    d.manager_id = uuid.UUID(manager_id or str(uuid.uuid4()))
    return d


def _make_approval(
    level: int = 1,
    approver_id: Optional[str] = None,
    status: str = "PENDING",
):
    a = MagicMock()
    a.id = uuid.UUID(str(uuid.uuid4()))
    a.approval_level = level
    a.approver_id = uuid.UUID(approver_id or str(uuid.uuid4()))
    a.status = status
    a.comments = None
    a.approved_at = None
    return a


def _mock_session() -> AsyncMock:
    session = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


# ---------------------------------------------------------------------------
# get_approval_chain — tested via create_approval_workflow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chain_manager_only_for_small_amount():
    """Amounts below THRESHOLD_FINANCE_HEAD get only 1 approver (manager)."""
    from api.services.approval_service import get_approval_chain

    manager = _make_user("manager")
    dept = _make_dept(manager_id=str(manager.id))
    tenant_id = str(uuid.uuid4())
    dept_id = str(dept.id)

    session = _mock_session()
    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        r = MagicMock()
        if call_count == 1:
            # select(Department)
            r.scalar_one_or_none.return_value = dept
        elif call_count == 2:
            # select(User) for manager
            r.scalar_one_or_none.return_value = manager
        return r

    session.execute.side_effect = side_effect

    chain = await get_approval_chain(
        session=session,
        tenant_id=tenant_id,
        entity_type="PURCHASE_REQUEST",
        amount_cents=THRESHOLD_FINANCE_HEAD - 1,  # just below threshold
        department_id=dept_id,
    )

    assert len(chain) == 1
    assert chain[0].role == "manager"
    assert chain[0].approval_level == 1


@pytest.mark.asyncio
async def test_chain_adds_finance_head_at_threshold():
    """Amounts >= THRESHOLD_FINANCE_HEAD require manager + finance_head."""
    from api.services.approval_service import get_approval_chain

    manager = _make_user("manager")
    finance_head = _make_user("finance_head")
    dept = _make_dept(manager_id=str(manager.id))
    tenant_id = str(uuid.uuid4())

    session = _mock_session()
    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        r = MagicMock()
        if call_count == 1:
            r.scalar_one_or_none.return_value = dept
        elif call_count == 2:
            r.scalar_one_or_none.return_value = manager
        elif call_count == 3:
            # get_role_user for finance_head
            r.scalars.return_value.first.return_value = finance_head
        return r

    session.execute.side_effect = side_effect

    chain = await get_approval_chain(
        session=session,
        tenant_id=tenant_id,
        entity_type="PURCHASE_REQUEST",
        amount_cents=THRESHOLD_FINANCE_HEAD,
        department_id=str(dept.id),
    )

    assert len(chain) == 2
    assert chain[0].role == "manager"
    assert chain[1].role == "finance_head"
    assert chain[1].approval_level == 2


@pytest.mark.asyncio
async def test_chain_adds_cfo_at_high_threshold():
    """Amounts >= THRESHOLD_CFO require all three approvers."""
    from api.services.approval_service import get_approval_chain

    manager = _make_user("manager")
    finance_head = _make_user("finance_head")
    cfo = _make_user("cfo")
    dept = _make_dept(manager_id=str(manager.id))
    tenant_id = str(uuid.uuid4())

    session = _mock_session()
    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        r = MagicMock()
        if call_count == 1:
            r.scalar_one_or_none.return_value = dept
        elif call_count == 2:
            r.scalar_one_or_none.return_value = manager
        elif call_count == 3:
            r.scalars.return_value.first.return_value = finance_head
        elif call_count == 4:
            r.scalars.return_value.first.return_value = cfo
        return r

    session.execute.side_effect = side_effect

    chain = await get_approval_chain(
        session=session,
        tenant_id=tenant_id,
        entity_type="PURCHASE_REQUEST",
        amount_cents=THRESHOLD_CFO,
        department_id=str(dept.id),
    )

    assert len(chain) == 3
    assert [s.role for s in chain] == ["manager", "finance_head", "cfo"]
    assert [s.approval_level for s in chain] == [1, 2, 3]


@pytest.mark.asyncio
async def test_chain_raises_if_no_manager():
    """Raises 422 when department has no active manager."""
    from api.services.approval_service import get_approval_chain

    dept = _make_dept()
    dept.manager_id = None  # no manager
    session = _mock_session()
    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        r = MagicMock()
        r.scalar_one_or_none.return_value = dept if call_count == 1 else None
        return r

    session.execute.side_effect = side_effect

    with pytest.raises(HTTPException) as exc_info:
        await get_approval_chain(
            session=session,
            tenant_id=str(uuid.uuid4()),
            entity_type="PURCHASE_REQUEST",
            amount_cents=100_00,
            department_id=str(dept.id),
        )

    assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# process_approval
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_approval_approve_final():
    """Single-step chain: approve → is_final True."""
    approver_id = str(uuid.uuid4())
    approval = _make_approval(level=1, approver_id=approver_id, status="PENDING")

    session = _mock_session()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [approval]
    session.execute.return_value = result_mock

    result = await process_approval(
        session=session,
        entity_type="PURCHASE_REQUEST",
        entity_id=str(uuid.uuid4()),
        approver_id=approver_id,
        action="approve",
    )

    assert result.is_final is True
    assert result.is_rejected is False
    assert approval.status == "APPROVED"
    assert approval.approved_at is not None


@pytest.mark.asyncio
async def test_process_approval_approve_not_final():
    """Multi-step chain: first approve → is_final False, next_approval set."""
    approver1_id = str(uuid.uuid4())
    approver2_id = str(uuid.uuid4())
    step1 = _make_approval(level=1, approver_id=approver1_id, status="PENDING")
    step2 = _make_approval(level=2, approver_id=approver2_id, status="PENDING")

    session = _mock_session()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [step1, step2]
    session.execute.return_value = result_mock

    result = await process_approval(
        session=session,
        entity_type="PURCHASE_REQUEST",
        entity_id=str(uuid.uuid4()),
        approver_id=approver1_id,
        action="approve",
    )

    assert result.is_final is False
    assert result.is_rejected is False
    assert result.next_approval is step2
    assert step1.status == "APPROVED"


@pytest.mark.asyncio
async def test_process_approval_reject_cancels_remaining():
    """Rejection cancels all remaining PENDING steps."""
    approver1_id = str(uuid.uuid4())
    approver2_id = str(uuid.uuid4())
    step1 = _make_approval(level=1, approver_id=approver1_id, status="PENDING")
    step2 = _make_approval(level=2, approver_id=approver2_id, status="PENDING")

    session = _mock_session()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [step1, step2]
    session.execute.return_value = result_mock

    result = await process_approval(
        session=session,
        entity_type="PURCHASE_REQUEST",
        entity_id=str(uuid.uuid4()),
        approver_id=approver1_id,
        action="reject",
        comment="Budget not justified",
    )

    assert result.is_rejected is True
    assert step1.status == "REJECTED"
    assert step1.comments == "Budget not justified"
    assert step2.status == "CANCELLED"


@pytest.mark.asyncio
async def test_process_approval_wrong_approver_raises_403():
    """Wrong approver raises HTTP 403."""
    correct_approver_id = str(uuid.uuid4())
    wrong_approver_id = str(uuid.uuid4())
    step = _make_approval(level=1, approver_id=correct_approver_id, status="PENDING")

    session = _mock_session()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [step]
    session.execute.return_value = result_mock

    with pytest.raises(HTTPException) as exc_info:
        await process_approval(
            session=session,
            entity_type="PURCHASE_REQUEST",
            entity_id=str(uuid.uuid4()),
            approver_id=wrong_approver_id,
            action="approve",
        )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_process_approval_no_pending_raises_400():
    """No pending steps raises HTTP 400."""
    step = _make_approval(level=1, status="APPROVED")

    session = _mock_session()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [step]
    session.execute.return_value = result_mock

    with pytest.raises(HTTPException) as exc_info:
        await process_approval(
            session=session,
            entity_type="PURCHASE_REQUEST",
            entity_id=str(uuid.uuid4()),
            approver_id=str(uuid.uuid4()),
            action="approve",
        )

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_process_approval_no_workflow_raises_404():
    """No approval records raises HTTP 404."""
    session = _mock_session()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    session.execute.return_value = result_mock

    with pytest.raises(HTTPException) as exc_info:
        await process_approval(
            session=session,
            entity_type="PURCHASE_REQUEST",
            entity_id=str(uuid.uuid4()),
            approver_id=str(uuid.uuid4()),
            action="approve",
        )

    assert exc_info.value.status_code == 404
