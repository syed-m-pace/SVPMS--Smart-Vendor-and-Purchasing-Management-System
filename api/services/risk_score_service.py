"""
Vendor Risk Score computation.

Risk score: 0 (lowest risk) → 100 (highest risk).

Factors:
  - Document compliance (30%): expired/missing docs raise score
  - Invoice exception rate (35%): EXCEPTION invoices as a fraction of total
  - Delivery performance (35%): late deliveries as a fraction of POs with deadlines
"""

from datetime import date, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.models.invoice import Invoice
from api.models.purchase_order import PurchaseOrder
from api.models.receipt import Receipt
from api.models.vendor import Vendor, VendorDocument

logger = structlog.get_logger()

# Thresholds for document expiry
_DOC_EXPIRY_EXPIRED_PENALTY = 100
_DOC_EXPIRY_WARNING_DAYS = 30
_DOC_EXPIRY_WARNING_PENALTY = 50


async def compute_vendor_risk_score(
    db: AsyncSession,
    vendor_id: str,
) -> Optional[int]:
    """
    Compute a 0–100 risk score for a vendor and persist it on the Vendor row.
    Returns the computed score, or None if the vendor is not found.
    """
    vendor_result = await db.execute(
        select(Vendor).where(Vendor.id == vendor_id, Vendor.deleted_at.is_(None))
    )
    vendor = vendor_result.scalar_one_or_none()
    if not vendor:
        return None

    today = date.today()
    warning_cutoff = today + timedelta(days=_DOC_EXPIRY_WARNING_DAYS)

    # ------------------------------------------------------------------
    # Factor 1: Document compliance (weight 30%)
    # ------------------------------------------------------------------
    doc_result = await db.execute(
        select(VendorDocument).where(VendorDocument.vendor_id == vendor_id)
    )
    docs = doc_result.scalars().all()

    doc_score = 0.0
    if docs:
        penalties = []
        for doc in docs:
            if doc.expiry_date is None:
                penalties.append(0)
            elif doc.expiry_date < today:
                penalties.append(_DOC_EXPIRY_EXPIRED_PENALTY)
            elif doc.expiry_date <= warning_cutoff:
                penalties.append(_DOC_EXPIRY_WARNING_PENALTY)
            else:
                penalties.append(0)
        doc_score = sum(penalties) / len(penalties)
    # If no documents: neutral (0 penalty)

    # ------------------------------------------------------------------
    # Factor 2: Invoice exception rate (weight 35%)
    # ------------------------------------------------------------------
    total_inv_result = await db.execute(
        select(func.count(Invoice.id)).where(
            Invoice.vendor_id == vendor_id,
            Invoice.status.in_(["MATCHED", "EXCEPTION", "DISPUTED", "APPROVED", "PAID"]),
        )
    )
    total_invoices = total_inv_result.scalar() or 0

    exception_inv_result = await db.execute(
        select(func.count(Invoice.id)).where(
            Invoice.vendor_id == vendor_id,
            Invoice.status.in_(["EXCEPTION", "DISPUTED"]),
        )
    )
    exception_invoices = exception_inv_result.scalar() or 0

    if total_invoices > 0:
        exception_rate = exception_invoices / total_invoices
        invoice_score = exception_rate * 100
    else:
        invoice_score = 0.0  # No history → assume low risk

    # ------------------------------------------------------------------
    # Factor 3: Late delivery rate (weight 35%)
    # ------------------------------------------------------------------
    # POs with an expected_delivery_date that have at least one receipt
    po_result = await db.execute(
        select(PurchaseOrder.id, PurchaseOrder.expected_delivery_date).where(
            PurchaseOrder.vendor_id == vendor_id,
            PurchaseOrder.expected_delivery_date.is_not(None),
            PurchaseOrder.status.in_(["ISSUED", "CLOSED"]),
        )
    )
    po_rows = po_result.all()

    late_count = 0
    po_with_deadline_count = len(po_rows)

    for po_id, deadline in po_rows:
        # Find the earliest CONFIRMED receipt for this PO
        receipt_result = await db.execute(
            select(func.min(Receipt.received_date)).where(
                Receipt.po_id == po_id,
                Receipt.status == "CONFIRMED",
            )
        )
        earliest_receipt = receipt_result.scalar()
        if earliest_receipt and earliest_receipt > deadline:
            late_count += 1
        elif earliest_receipt is None:
            # No receipt yet — if past deadline, count as late
            if deadline < today:
                late_count += 1

    if po_with_deadline_count > 0:
        late_rate = late_count / po_with_deadline_count
        delivery_score = late_rate * 100
    else:
        delivery_score = 0.0  # No PO history → assume low risk

    # ------------------------------------------------------------------
    # Weighted composite
    # ------------------------------------------------------------------
    raw_score = (
        doc_score * 0.30
        + invoice_score * 0.35
        + delivery_score * 0.35
    )
    final_score = max(0, min(100, round(raw_score)))

    vendor.risk_score = final_score
    await db.flush()

    logger.info(
        "vendor_risk_score_computed",
        vendor_id=vendor_id,
        risk_score=final_score,
        doc_score=round(doc_score, 1),
        invoice_score=round(invoice_score, 1),
        delivery_score=round(delivery_score, 1),
    )

    return final_score
