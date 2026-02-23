# api/routes/match.py
"""
Manual 3-way match trigger endpoint.
From 01_BACKEND.md OpenAPI /api/v1/match.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.middleware.auth import get_current_user
from api.middleware.tenant import get_db_with_tenant
from api.middleware.authorization import require_roles
from api.models.invoice import Invoice
from api.models.purchase_order import PurchaseOrder
from api.services.matching_service import (
    three_way_match_invoice,
    match_result_to_dict,
)

logger = structlog.get_logger()
router = APIRouter()


class MatchRequest(BaseModel):
    po_id: str
    invoice_id: str
    tolerance_percent: Optional[float] = 2.0


@router.post("")
async def run_match(
    body: MatchRequest,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("finance", "finance_head", "cfo", "admin", "manager")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    """Run 3-way match for an invoice against its PO and receipts."""
    # Validate PO exists
    po = await db.get(PurchaseOrder, body.po_id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")

    # Validate invoice exists
    invoice = await db.get(Invoice, body.invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    tolerance_config = {
        "price_variance_percent": body.tolerance_percent or 2.0,
        "min_variance_cents": 1000,
    }

    result = await three_way_match_invoice(
        db, body.po_id, body.invoice_id, tolerance_config
    )

    # Update invoice status based on result
    if result.status == "MATCHED":
        invoice.status = "MATCHED"
        invoice.match_status = "PASS"
        invoice.match_exceptions = None
    else:
        invoice.status = "EXCEPTION"
        invoice.match_status = "FAIL"
        invoice.match_exceptions = match_result_to_dict(result)

    await db.flush()
    logger.info(
        "manual_match_triggered",
        invoice_id=body.invoice_id,
        po_id=body.po_id,
        result=result.status,
    )

    return match_result_to_dict(result)
