"""
Unit tests for api/services/matching_service.py

Tests the core 3-way match algorithm:
  - QTY_MISMATCH: zero-tolerance quantity check
  - PRICE_VARIANCE: 2% tolerance, min 1000 cents
  - MISSING_INVOICE_LINE: invoice has no line for a PO line
  - NO_PO_LINES: PO has no lines
  - Full MATCHED result on clean data
"""

import uuid
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.services.matching_service import (
    DEFAULT_TOLERANCE,
    MatchResult,
    three_way_match_invoice,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_po_line(
    description: str = "Widget A",
    quantity: int = 10,
    unit_price_cents: int = 10_000,
    po_id: Optional[str] = None,
    line_id: Optional[str] = None,
):
    line = MagicMock()
    line.id = uuid.UUID(line_id or str(uuid.uuid4()))
    line.po_id = uuid.UUID(po_id or str(uuid.uuid4()))
    line.description = description
    line.quantity = quantity
    line.unit_price_cents = unit_price_cents
    return line


def _make_invoice_line(
    description: str = "Widget A",
    quantity: int = 10,
    unit_price_cents: int = 10_000,
    invoice_id: Optional[str] = None,
):
    line = MagicMock()
    line.id = uuid.UUID(str(uuid.uuid4()))
    line.invoice_id = uuid.UUID(invoice_id or str(uuid.uuid4()))
    line.description = description
    line.quantity = quantity
    line.unit_price_cents = unit_price_cents
    return line


def _build_session(po_lines, receipt_qty_map, invoice_lines):
    """
    Build an AsyncMock session whose execute() returns results in order:
      1. PO lines (PoLineItem SELECT)
      2. Receipt aggregation (ReceiptLineItem GROUP BY)
      3. Invoice lines (InvoiceLineItem SELECT)
    """
    session = AsyncMock()
    call_count = 0

    # Receipt data: list of row objects with po_line_item_id + total_received
    receipt_rows = []
    for po_line_id, qty in receipt_qty_map.items():
        row = MagicMock()
        row.po_line_item_id = uuid.UUID(po_line_id)
        row.total_received = qty
        receipt_rows.append(row)

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        r = MagicMock()
        if call_count == 1:
            # PO lines
            r.scalars.return_value.all.return_value = po_lines
        elif call_count == 2:
            # Receipt aggregation
            r.all.return_value = receipt_rows
        else:
            # Invoice lines
            r.scalars.return_value.all.return_value = invoice_lines
        return r

    session.execute.side_effect = side_effect
    return session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_matched_clean_data():
    """Perfect match: qty and price both within tolerance → MATCHED."""
    po_line = _make_po_line(description="Widget A", quantity=10, unit_price_cents=10_000)
    inv_line = _make_invoice_line(description="Widget A", quantity=10, unit_price_cents=10_000)
    session = _build_session(
        po_lines=[po_line],
        receipt_qty_map={str(po_line.id): 10},
        invoice_lines=[inv_line],
    )

    result = await three_way_match_invoice(
        session=session,
        po_id=str(uuid.uuid4()),
        invoice_id=str(uuid.uuid4()),
    )

    assert result.status == "MATCHED"
    assert result.exceptions == []


@pytest.mark.asyncio
async def test_qty_mismatch_zero_tolerance():
    """Invoice qty differs from received qty → QTY_MISMATCH exception."""
    po_line = _make_po_line(description="Widget A", quantity=10, unit_price_cents=10_000)
    # Received 8, invoice says 10
    inv_line = _make_invoice_line(description="Widget A", quantity=10, unit_price_cents=10_000)
    session = _build_session(
        po_lines=[po_line],
        receipt_qty_map={str(po_line.id): 8},  # only 8 received
        invoice_lines=[inv_line],
    )

    result = await three_way_match_invoice(
        session=session,
        po_id=str(uuid.uuid4()),
        invoice_id=str(uuid.uuid4()),
    )

    assert result.status == "EXCEPTION"
    exception_types = [e.type for e in result.exceptions]
    assert "QTY_MISMATCH" in exception_types
    exc = next(e for e in result.exceptions if e.type == "QTY_MISMATCH")
    assert exc.details["received"] == 8
    assert exc.details["invoiced"] == 10


@pytest.mark.asyncio
async def test_price_variance_within_tolerance():
    """Price 1.5% above PO price → within 2% tolerance → MATCHED."""
    po_price = 100_000  # 100,000 cents
    inv_price = 101_500  # 1.5% above — within tolerance
    po_line = _make_po_line(description="Server", quantity=1, unit_price_cents=po_price)
    inv_line = _make_invoice_line(description="Server", quantity=1, unit_price_cents=inv_price)
    session = _build_session(
        po_lines=[po_line],
        receipt_qty_map={str(po_line.id): 1},
        invoice_lines=[inv_line],
    )

    result = await three_way_match_invoice(
        session=session,
        po_id=str(uuid.uuid4()),
        invoice_id=str(uuid.uuid4()),
    )

    assert result.status == "MATCHED"


@pytest.mark.asyncio
async def test_price_variance_exceeds_tolerance():
    """Price 5% above PO price → exceeds 2% tolerance → PRICE_VARIANCE exception."""
    po_price = 100_000
    inv_price = 105_000  # 5% above
    po_line = _make_po_line(description="Server", quantity=1, unit_price_cents=po_price)
    inv_line = _make_invoice_line(description="Server", quantity=1, unit_price_cents=inv_price)
    session = _build_session(
        po_lines=[po_line],
        receipt_qty_map={str(po_line.id): 1},
        invoice_lines=[inv_line],
    )

    result = await three_way_match_invoice(
        session=session,
        po_id=str(uuid.uuid4()),
        invoice_id=str(uuid.uuid4()),
    )

    assert result.status == "EXCEPTION"
    exception_types = [e.type for e in result.exceptions]
    assert "PRICE_VARIANCE" in exception_types
    exc = next(e for e in result.exceptions if e.type == "PRICE_VARIANCE")
    assert exc.details["po_price_cents"] == po_price
    assert exc.details["invoice_price_cents"] == inv_price


@pytest.mark.asyncio
async def test_price_variance_below_min_cents_ignored():
    """Variance below min_variance_cents (1000 cents) is always ignored."""
    po_price = 5_000     # 5,000 cents
    inv_price = 5_500    # 500 cents difference — below 1000 min threshold
    po_line = _make_po_line(description="Cable", quantity=1, unit_price_cents=po_price)
    inv_line = _make_invoice_line(description="Cable", quantity=1, unit_price_cents=inv_price)
    session = _build_session(
        po_lines=[po_line],
        receipt_qty_map={str(po_line.id): 1},
        invoice_lines=[inv_line],
    )

    result = await three_way_match_invoice(
        session=session,
        po_id=str(uuid.uuid4()),
        invoice_id=str(uuid.uuid4()),
    )

    # 500 cents < min_variance_cents 1000 → no PRICE_VARIANCE exception
    assert result.status == "MATCHED"


@pytest.mark.asyncio
async def test_missing_invoice_line():
    """PO has a line that does not appear in the invoice → MISSING_INVOICE_LINE."""
    po_line = _make_po_line(description="Unique Item XYZ", quantity=5, unit_price_cents=20_000)
    # Invoice has a different item
    inv_line = _make_invoice_line(description="Different Item", quantity=5, unit_price_cents=20_000)
    session = _build_session(
        po_lines=[po_line],
        receipt_qty_map={str(po_line.id): 5},
        invoice_lines=[inv_line],
    )

    result = await three_way_match_invoice(
        session=session,
        po_id=str(uuid.uuid4()),
        invoice_id=str(uuid.uuid4()),
    )

    assert result.status == "EXCEPTION"
    assert any(e.type == "MISSING_INVOICE_LINE" for e in result.exceptions)


@pytest.mark.asyncio
async def test_no_po_lines_returns_exception():
    """PO with no line items returns EXCEPTION with NO_PO_LINES."""
    session = _build_session(
        po_lines=[],
        receipt_qty_map={},
        invoice_lines=[],
    )

    result = await three_way_match_invoice(
        session=session,
        po_id=str(uuid.uuid4()),
        invoice_id=str(uuid.uuid4()),
    )

    assert result.status == "EXCEPTION"
    assert any(e.type == "NO_PO_LINES" for e in result.exceptions)


@pytest.mark.asyncio
async def test_multiple_lines_all_match():
    """Multiple PO lines all match → MATCHED with no exceptions."""
    po_line_1 = _make_po_line(description="Item A", quantity=5, unit_price_cents=10_000)
    po_line_2 = _make_po_line(description="Item B", quantity=3, unit_price_cents=50_000)
    inv_line_1 = _make_invoice_line(description="Item A", quantity=5, unit_price_cents=10_000)
    inv_line_2 = _make_invoice_line(description="Item B", quantity=3, unit_price_cents=50_000)
    session = _build_session(
        po_lines=[po_line_1, po_line_2],
        receipt_qty_map={
            str(po_line_1.id): 5,
            str(po_line_2.id): 3,
        },
        invoice_lines=[inv_line_1, inv_line_2],
    )

    result = await three_way_match_invoice(
        session=session,
        po_id=str(uuid.uuid4()),
        invoice_id=str(uuid.uuid4()),
    )

    assert result.status == "MATCHED"
    assert result.exceptions == []


@pytest.mark.asyncio
async def test_custom_tolerance_config():
    """Custom tolerance_config overrides default 2% threshold."""
    po_price = 100_000
    inv_price = 103_000  # 3% above — exceeds default 2% but within custom 5%
    po_line = _make_po_line(description="Widget", quantity=1, unit_price_cents=po_price)
    inv_line = _make_invoice_line(description="Widget", quantity=1, unit_price_cents=inv_price)
    session = _build_session(
        po_lines=[po_line],
        receipt_qty_map={str(po_line.id): 1},
        invoice_lines=[inv_line],
    )

    result = await three_way_match_invoice(
        session=session,
        po_id=str(uuid.uuid4()),
        invoice_id=str(uuid.uuid4()),
        tolerance_config={"price_variance_percent": 5.0, "min_variance_cents": 1000},
    )

    assert result.status == "MATCHED"


@pytest.mark.asyncio
async def test_case_insensitive_description_match():
    """Description matching is case-insensitive (both lowercased before lookup)."""
    po_line = _make_po_line(description="Server Model X", quantity=2, unit_price_cents=200_000)
    # Invoice has different casing
    inv_line = _make_invoice_line(description="server model x", quantity=2, unit_price_cents=200_000)
    session = _build_session(
        po_lines=[po_line],
        receipt_qty_map={str(po_line.id): 2},
        invoice_lines=[inv_line],
    )

    result = await three_way_match_invoice(
        session=session,
        po_id=str(uuid.uuid4()),
        invoice_id=str(uuid.uuid4()),
    )

    assert result.status == "MATCHED"
