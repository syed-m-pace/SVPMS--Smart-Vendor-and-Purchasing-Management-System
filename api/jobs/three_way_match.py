# api/jobs/three_way_match.py
"""
Three-Way Match background worker.
Called as BackgroundTask after OCR completes or via manual trigger.
From 01_BACKEND.md §5.3.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.database import AsyncSessionLocal, set_tenant_context
from api.models.invoice import Invoice
from api.models.purchase_order import PurchaseOrder
from api.models.receipt import Receipt
from api.services.matching_service import three_way_match_invoice, match_result_to_dict
from api.services.audit_service import create_audit_log

logger = structlog.get_logger()


async def run_three_way_match(invoice_id: str, tenant_id: str):
    """
    Run 3-way match: PO vs Receipt vs Invoice.
    Called as BackgroundTask after OCR completes.
    """
    async with AsyncSessionLocal() as session:
        await set_tenant_context(session, tenant_id)

        try:
            invoice = await session.get(Invoice, invoice_id)
            if not invoice or not invoice.po_id:
                logger.warning(
                    "match_skipped",
                    invoice_id=invoice_id,
                    reason="no invoice or no po_id",
                )
                return

            po = await session.get(PurchaseOrder, invoice.po_id)
            if not po:
                logger.warning("match_skipped", invoice_id=invoice_id, reason="po not found")
                return

            # Run matching algorithm
            result = three_way_match_invoice(session, str(po.id), invoice_id)
            # Await the coroutine
            result = await result

            before = {"status": invoice.status, "match_status": invoice.match_status}

            if result.status == "MATCHED":
                invoice.status = "MATCHED"
                invoice.match_status = "PASS"
                invoice.match_exceptions = None
            else:
                invoice.status = "EXCEPTION"
                invoice.match_status = "FAIL"
                invoice.match_exceptions = match_result_to_dict(result)

            after = {"status": invoice.status, "match_status": invoice.match_status}

            await create_audit_log(
                session,
                tenant_id=tenant_id,
                actor_id="system",
                action="THREE_WAY_MATCH",
                entity_type="INVOICE",
                entity_id=invoice_id,
                before_state=before,
                after_state=after,
            )

            await session.commit()
            logger.info(
                "three_way_match_complete",
                invoice_id=invoice_id,
                result=result.status,
                exceptions_count=len(result.exceptions),
            )

        except Exception as e:
            await session.rollback()
            logger.error(
                "three_way_match_failed", invoice_id=invoice_id, error=str(e)
            )
