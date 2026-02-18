# api/services/matching_service.py
"""
Three-Way Match: Purchase Order vs Receipt vs Invoice.

Matching Rules (from 01_BACKEND.md §2.2):
  1. Line-by-line comparison of quantities and prices
  2. Quantity: ZERO tolerance (must match exactly)
  3. Price: Configurable tolerance (default 2%)
  4. Aggregate results into MATCHED or specific exception codes
"""

from dataclasses import dataclass, asdict
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.models.purchase_order import PurchaseOrder, PoLineItem
from api.models.receipt import Receipt, ReceiptLineItem
from api.models.invoice import Invoice, InvoiceLineItem

logger = structlog.get_logger()


@dataclass
class MatchException:
    type: str  # QTY_MISMATCH, PRICE_VARIANCE, MISSING_INVOICE_LINE
    po_line_id: str
    description: str
    details: dict


@dataclass
class MatchResult:
    status: str  # MATCHED, EXCEPTION
    invoice_id: str
    exceptions: List[MatchException]
    message: str


DEFAULT_TOLERANCE = {
    "price_variance_percent": 2.0,
    "min_variance_cents": 1000,  # Ignore variances < $10
}


async def three_way_match_invoice(
    session: AsyncSession,
    po_id: str,
    invoice_id: str,
    tolerance_config: Optional[dict] = None,
) -> MatchResult:
    """
    Perform 3-way match: Purchase Order vs Receipt vs Invoice.

    Returns MatchResult with status and exception details.
    """
    if tolerance_config is None:
        tolerance_config = DEFAULT_TOLERANCE.copy()

    # Step 1: Load PO line items
    po_lines_result = await session.execute(
        select(PoLineItem).where(PoLineItem.po_id == po_id)
    )
    po_lines = po_lines_result.scalars().all()

    if not po_lines:
        return MatchResult(
            status="EXCEPTION",
            invoice_id=invoice_id,
            exceptions=[
                MatchException(
                    type="NO_PO_LINES",
                    po_line_id="",
                    description="Purchase order has no line items",
                    details={"po_id": po_id},
                )
            ],
            message="Purchase order has no line items to match against.",
        )

    # Step 2: Load Receipt line items (aggregate if multiple receipts)
    receipt_result = await session.execute(
        select(
            ReceiptLineItem.po_line_item_id,
            func.sum(ReceiptLineItem.quantity_received).label("total_received"),
        )
        .join(Receipt)
        .where(Receipt.po_id == po_id)
        .group_by(ReceiptLineItem.po_line_item_id)
    )
    receipt_data = receipt_result.all()
    receipt_qty_map = {
        str(row.po_line_item_id): row.total_received for row in receipt_data
    }

    # Step 3: Load Invoice line items
    invoice_lines_result = await session.execute(
        select(InvoiceLineItem).where(InvoiceLineItem.invoice_id == invoice_id)
    )
    invoice_lines = invoice_lines_result.scalars().all()

    # Create lookup map by description (simplified — use fuzzy matching in production)
    invoice_map = {il.description.strip().lower(): il for il in invoice_lines}

    # Step 4: Line-by-line comparison
    exceptions: List[MatchException] = []

    for po_line in po_lines:
        received_qty = receipt_qty_map.get(str(po_line.id), 0)

        # Find matching invoice line
        invoice_line = invoice_map.get(po_line.description.strip().lower())

        if not invoice_line:
            exceptions.append(
                MatchException(
                    type="MISSING_INVOICE_LINE",
                    po_line_id=str(po_line.id),
                    description=po_line.description,
                    details={
                        "ordered_qty": po_line.quantity,
                        "received_qty": received_qty,
                    },
                )
            )
            continue

        # Rule 1: Quantity Check (ZERO TOLERANCE)
        if invoice_line.quantity != received_qty:
            exceptions.append(
                MatchException(
                    type="QTY_MISMATCH",
                    po_line_id=str(po_line.id),
                    description=po_line.description,
                    details={
                        "ordered": po_line.quantity,
                        "received": received_qty,
                        "invoiced": invoice_line.quantity,
                    },
                )
            )

        # Rule 2: Price Check (WITH TOLERANCE)
        price_diff_cents = abs(
            invoice_line.unit_price_cents - po_line.unit_price_cents
        )
        tolerance_cents = max(
            tolerance_config["min_variance_cents"],
            int(
                po_line.unit_price_cents
                * tolerance_config["price_variance_percent"]
                / 100
            ),
        )

        if price_diff_cents > tolerance_cents:
            exceptions.append(
                MatchException(
                    type="PRICE_VARIANCE",
                    po_line_id=str(po_line.id),
                    description=po_line.description,
                    details={
                        "po_price_cents": po_line.unit_price_cents,
                        "invoice_price_cents": invoice_line.unit_price_cents,
                        "variance_cents": price_diff_cents,
                        "tolerance_cents": tolerance_cents,
                        "variance_pct": round(
                            (price_diff_cents / po_line.unit_price_cents) * 100, 2
                        )
                        if po_line.unit_price_cents
                        else 0,
                    },
                )
            )

    # Step 5: Build result
    if not exceptions:
        logger.info("three_way_match_passed", invoice_id=invoice_id, po_id=po_id)
        return MatchResult(
            status="MATCHED",
            invoice_id=invoice_id,
            exceptions=[],
            message="Invoice matched successfully. Payment queued.",
        )
    else:
        logger.warning(
            "three_way_match_exceptions",
            invoice_id=invoice_id,
            po_id=po_id,
            count=len(exceptions),
        )
        return MatchResult(
            status="EXCEPTION",
            invoice_id=invoice_id,
            exceptions=exceptions,
            message=f"{len(exceptions)} exception(s) found during 3-way match.",
        )


def match_result_to_dict(result: MatchResult) -> dict:
    """Convert MatchResult to JSON-serializable dict."""
    return {
        "status": result.status,
        "invoice_id": result.invoice_id,
        "exceptions": [asdict(e) for e in result.exceptions],
        "message": result.message,
    }
