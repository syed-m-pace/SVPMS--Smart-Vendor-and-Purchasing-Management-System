# api/services/ocr.py
from google.cloud import documentai_v1 as documentai
from api.config import settings
import structlog

logger = structlog.get_logger()


def extract_invoice_data(file_bytes: bytes) -> dict:
    """Extract invoice fields using Google Document AI.

    Returns dict with: invoice_number, total_cents, confidence.
    """
    if not settings.DOCUMENT_AI_PROCESSOR:
        logger.warning("document_ai_not_configured")
        return {}

    client = documentai.DocumentProcessorServiceClient()
    result = client.process_document(
        request=documentai.ProcessRequest(
            name=settings.DOCUMENT_AI_PROCESSOR,
            raw_document=documentai.RawDocument(
                content=file_bytes, mime_type="application/pdf"
            ),
        )
    )

    fields = {}
    for e in result.document.entities:
        if e.type_ == "invoice_id":
            fields["invoice_number"] = e.mention_text
        elif e.type_ == "total_amount":
            fields["total_cents"] = int(
                float(e.mention_text.replace(",", "").replace("₹", "")) * 100
            )

    fields["confidence"] = min(
        (e.confidence for e in result.document.entities), default=0
    )
    logger.info(
        "ocr_extracted",
        fields=list(fields.keys()),
        confidence=fields.get("confidence"),
    )
    return fields
