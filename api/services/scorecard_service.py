"""
Supplier Scorecard Engine.

Computes vendor KPIs from PO, Receipt, and Invoice history:
  - on_time_delivery_rate: % of POs delivered by expected_delivery_date
  - invoice_acceptance_rate: % of invoices that reached MATCHED/APPROVED/PAID (vs EXCEPTION)
  - rfq_response_rate: % of RFQs the vendor was invited to and actually submitted a bid
  - avg_invoice_processing_days: mean days from invoice upload to PAID
  - po_fulfillment_rate: % of POs fully received (CONFIRMED receipt exists)
  - composite_score: weighted average 0-100 for overall performance

All metrics require at least one completed interaction to be meaningful.
"""

from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.models.invoice import Invoice
from api.models.purchase_order import PurchaseOrder
from api.models.receipt import Receipt
from api.models.rfq import Rfq, RfqBid

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Weights for composite score (must sum to 1.0)
# ---------------------------------------------------------------------------
_WEIGHTS = {
    "on_time_delivery_rate": 0.30,
    "invoice_acceptance_rate": 0.30,
    "po_fulfillment_rate": 0.25,
    "rfq_response_rate": 0.15,
}


@dataclass
class VendorScorecard:
    vendor_id: str
    # Core KPIs (0-100 scale, None = insufficient data)
    on_time_delivery_rate: Optional[float]   # % POs received by expected_delivery_date
    invoice_acceptance_rate: Optional[float] # % invoices matched without manual override
    po_fulfillment_rate: Optional[float]     # % POs with a CONFIRMED receipt
    rfq_response_rate: Optional[float]       # % invited RFQs that vendor bid on
    # Volume metrics (informational)
    total_pos: int
    total_invoices: int
    total_rfqs_invited: int
    avg_invoice_processing_days: Optional[float]  # days upload→paid
    # Composite
    composite_score: Optional[float]             # 0-100 weighted average


async def compute_vendor_scorecard(
    db: AsyncSession,
    vendor_id: str,
) -> VendorScorecard:
    """
    Compute all scorecard KPIs for a single vendor.
    Uses only data already present in the database — no new tables required.
    """
    vid = str(vendor_id)

    # ── 1. On-time Delivery Rate ────────────────────────────────────────────
    # POs with an expected_delivery_date AND at least one CONFIRMED receipt
    pos_with_deadline_result = await db.execute(
        select(
            PurchaseOrder.id,
            PurchaseOrder.expected_delivery_date,
        ).where(
            PurchaseOrder.vendor_id == vendor_id,
            PurchaseOrder.expected_delivery_date.isnot(None),
            PurchaseOrder.deleted_at.is_(None),
        )
    )
    pos_with_deadline = pos_with_deadline_result.all()
    total_deadline_pos = len(pos_with_deadline)

    on_time_count = 0
    if total_deadline_pos > 0:
        for po_row in pos_with_deadline:
            receipt_result = await db.execute(
                select(func.min(Receipt.receipt_date)).where(
                    Receipt.po_id == po_row.id,
                    Receipt.status == "CONFIRMED",
                )
            )
            earliest_receipt_date = receipt_result.scalar()
            if earliest_receipt_date is not None:
                deadline = po_row.expected_delivery_date
                # deadline is a date object; earliest_receipt_date may be date
                if isinstance(earliest_receipt_date, datetime):
                    earliest_receipt_date = earliest_receipt_date.date()
                if isinstance(deadline, datetime):
                    deadline = deadline.date()
                if earliest_receipt_date <= deadline:
                    on_time_count += 1

    on_time_delivery_rate: Optional[float] = (
        round(on_time_count / total_deadline_pos * 100, 1)
        if total_deadline_pos > 0
        else None
    )

    # ── 2. Invoice Acceptance Rate ──────────────────────────────────────────
    # Invoices that were matched (MATCHED/APPROVED/PAID) vs total completed
    invoice_totals_result = await db.execute(
        select(
            Invoice.status,
            func.count(Invoice.id).label("cnt"),
        )
        .where(
            Invoice.vendor_id == vendor_id,
            Invoice.status.in_(["MATCHED", "APPROVED", "PAID", "EXCEPTION", "DISPUTED"]),
        )
        .group_by(Invoice.status)
    )
    invoice_totals = {row.status: row.cnt for row in invoice_totals_result.all()}
    accepted = (
        invoice_totals.get("MATCHED", 0)
        + invoice_totals.get("APPROVED", 0)
        + invoice_totals.get("PAID", 0)
    )
    total_completed_invoices = sum(invoice_totals.values())

    invoice_acceptance_rate: Optional[float] = (
        round(accepted / total_completed_invoices * 100, 1)
        if total_completed_invoices > 0
        else None
    )

    # ── 3. PO Fulfillment Rate ──────────────────────────────────────────────
    total_pos_result = await db.execute(
        select(func.count(PurchaseOrder.id)).where(
            PurchaseOrder.vendor_id == vendor_id,
            PurchaseOrder.status.in_(["ISSUED", "ACKNOWLEDGED", "PARTIALLY_RECEIVED", "FULLY_RECEIVED", "CLOSED"]),
            PurchaseOrder.deleted_at.is_(None),
        )
    )
    total_pos = int(total_pos_result.scalar() or 0)

    fulfilled_pos_result = await db.execute(
        select(func.count(func.distinct(Receipt.po_id))).where(
            Receipt.po_id.in_(
                select(PurchaseOrder.id).where(
                    PurchaseOrder.vendor_id == vendor_id,
                    PurchaseOrder.deleted_at.is_(None),
                )
            ),
            Receipt.status == "CONFIRMED",
        )
    )
    fulfilled_pos = int(fulfilled_pos_result.scalar() or 0)

    po_fulfillment_rate: Optional[float] = (
        round(fulfilled_pos / total_pos * 100, 1)
        if total_pos > 0
        else None
    )

    # ── 4. RFQ Response Rate ────────────────────────────────────────────────
    # RFQs where a bid row exists for this vendor (invited) vs bids submitted
    rfq_invited_result = await db.execute(
        select(func.count(func.distinct(RfqBid.rfq_id))).where(
            RfqBid.vendor_id == vendor_id,
        )
    )
    total_rfqs_invited = int(rfq_invited_result.scalar() or 0)

    rfq_bid_submitted_result = await db.execute(
        select(func.count(func.distinct(RfqBid.rfq_id))).where(
            RfqBid.vendor_id == vendor_id,
            RfqBid.status.in_(["SUBMITTED", "AWARDED"]),
        )
    )
    rfq_bids_submitted = int(rfq_bid_submitted_result.scalar() or 0)

    rfq_response_rate: Optional[float] = (
        round(rfq_bids_submitted / total_rfqs_invited * 100, 1)
        if total_rfqs_invited > 0
        else None
    )

    # ── 5. Avg Invoice Processing Days ─────────────────────────────────────
    paid_invoices_result = await db.execute(
        select(Invoice.created_at, Invoice.paid_at).where(
            Invoice.vendor_id == vendor_id,
            Invoice.status == "PAID",
            Invoice.paid_at.isnot(None),
        )
    )
    paid_invoices = paid_invoices_result.all()
    avg_processing_days: Optional[float] = None
    if paid_invoices:
        total_days = sum(
            (row.paid_at - row.created_at).days
            for row in paid_invoices
            if row.paid_at and row.created_at
        )
        avg_processing_days = round(total_days / len(paid_invoices), 1)

    # ── 6. Composite Score ──────────────────────────────────────────────────
    composite_score: Optional[float] = None
    available = {
        "on_time_delivery_rate": on_time_delivery_rate,
        "invoice_acceptance_rate": invoice_acceptance_rate,
        "po_fulfillment_rate": po_fulfillment_rate,
        "rfq_response_rate": rfq_response_rate,
    }
    available_kpis = {k: v for k, v in available.items() if v is not None}
    if available_kpis:
        total_weight = sum(_WEIGHTS[k] for k in available_kpis)
        weighted_sum = sum(_WEIGHTS[k] * v for k, v in available_kpis.items())
        composite_score = round(weighted_sum / total_weight, 1)

    logger.info(
        "scorecard_computed",
        vendor_id=vid,
        composite_score=composite_score,
        total_pos=total_pos,
        total_invoices=total_completed_invoices,
    )

    return VendorScorecard(
        vendor_id=vid,
        on_time_delivery_rate=on_time_delivery_rate,
        invoice_acceptance_rate=invoice_acceptance_rate,
        po_fulfillment_rate=po_fulfillment_rate,
        rfq_response_rate=rfq_response_rate,
        total_pos=total_pos,
        total_invoices=total_completed_invoices,
        total_rfqs_invited=total_rfqs_invited,
        avg_invoice_processing_days=avg_processing_days,
        composite_score=composite_score,
    )
