# api/jobs/invoice_ocr.py
"""
Invoice OCR background worker using Google Document AI.
From 01_BACKEND.md §5.2.

Runs as FastAPI BackgroundTask (in-process).
Downloads PDF from R2, extracts structured data, updates invoice,
then auto-triggers 3-way match if PO exists.
"""

import structlog

from api.database import AsyncSessionLocal, set_tenant_context
from api.models.invoice import Invoice
from api.services.ocr import (
    SUPPORTED_MIME_TYPES,
    extract_invoice_data,
    infer_mime_type_from_key,
)
from api.services.storage import r2_client
from api.services.audit_service import create_audit_log

logger = structlog.get_logger()


async def process_invoice_ocr(invoice_id: str, tenant_id: str):
    """
    Process invoice OCR using Google Document AI.
    Runs as FastAPI BackgroundTask (in-process).
    """
    async with AsyncSessionLocal() as session:
        await set_tenant_context(session, tenant_id)

        try:
            # 1. Fetch invoice
            invoice = await session.get(Invoice, invoice_id)
            if not invoice:
                logger.error("ocr_invoice_not_found", invoice_id=invoice_id)
                return

            if not invoice.document_url:
                logger.warning("ocr_no_document", invoice_id=invoice_id)
                return

            document_key = r2_client.extract_key(invoice.document_url)
            if not document_key:
                logger.warning(
                    "ocr_invalid_document_reference",
                    invoice_id=invoice_id,
                    document_url=invoice.document_url,
                )
                invoice.ocr_status = "FAILED"
                await session.commit()
                return

            mime_type = infer_mime_type_from_key(document_key)
            if mime_type not in SUPPORTED_MIME_TYPES:
                logger.warning(
                    "ocr_unsupported_format",
                    invoice_id=invoice_id,
                    mime_type=mime_type,
                    document_key=document_key,
                )
                invoice.ocr_status = "UNSUPPORTED_FORMAT"
                await session.commit()
                return

            # 2. Download from R2
            try:
                file_bytes = r2_client.download(document_key)
            except Exception as e:
                logger.error(
                    "ocr_download_failed",
                    invoice_id=invoice_id,
                    document_url=invoice.document_url,
                    document_key=document_key,
                    error=str(e),
                )
                invoice.ocr_status = "FAILED"
                await session.commit()
                return

            # 3. Run Google Document AI
            ocr_data = extract_invoice_data(file_bytes, mime_type=mime_type)

            if not ocr_data:
                logger.warning("ocr_no_data_extracted", invoice_id=invoice_id)
                invoice.ocr_status = "FAILED"
                await session.commit()
                return

            # 4. Update invoice with extracted data
            confidence = ocr_data.get("confidence", 0)
            before = {
                "ocr_status": getattr(invoice, "ocr_status", None),
                "invoice_number": invoice.invoice_number,
                "total_cents": invoice.total_cents,
                "document_url": invoice.document_url,
            }

            invoice.ocr_status = "COMPLETE" if confidence >= 0.85 else "LOW_CONFIDENCE"
            invoice.ocr_data = ocr_data

            # Only overwrite fields if OCR found them
            if "invoice_number" in ocr_data and not invoice.invoice_number:
                invoice.invoice_number = ocr_data["invoice_number"]
            if "total_cents" in ocr_data and not invoice.total_cents:
                invoice.total_cents = ocr_data["total_cents"]

            after = {
                "ocr_status": invoice.ocr_status,
                "invoice_number": invoice.invoice_number,
                "total_cents": invoice.total_cents,
                "document_url": invoice.document_url,
            }

            await create_audit_log(
                session,
                tenant_id=tenant_id,
                actor_id="system",
                action="INVOICE_OCR",
                entity_type="INVOICE",
                entity_id=invoice_id,
                before_state=before,
                after_state=after,
            )

            await session.commit()
            logger.info(
                "ocr_complete",
                invoice_id=invoice_id,
                confidence=confidence,
                fields_extracted=list(ocr_data.keys()),
            )

            # 5. Auto-trigger 3-way match if PO exists
            if invoice.po_id:
                from api.jobs.three_way_match import run_three_way_match

                await run_three_way_match(invoice_id, tenant_id)

        except Exception as e:
            await session.rollback()
            logger.error("ocr_failed", invoice_id=invoice_id, error=str(e))
            # Try to mark as failed
            try:
                async with AsyncSessionLocal() as err_session:
                    await set_tenant_context(err_session, tenant_id)
                    inv = await err_session.get(Invoice, invoice_id)
                    if inv:
                        inv.ocr_status = "FAILED"
                        await err_session.commit()
            except Exception as recovery_err:
                logger.error(
                    "ocr_failed_recovery",
                    invoice_id=invoice_id,
                    error=str(recovery_err),
                )
