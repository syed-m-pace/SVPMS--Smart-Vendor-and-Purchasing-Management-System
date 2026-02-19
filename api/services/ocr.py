# api/services/ocr.py
from google.cloud import documentai_v1 as documentai
from api.config import settings
import structlog
from typing import Optional

logger = structlog.get_logger()


SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}


def infer_mime_type_from_key(file_key: Optional[str]) -> str:
    if not file_key or "." not in file_key:
        return "application/octet-stream"
    ext = file_key.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        return "application/pdf"
    if ext in ("jpg", "jpeg"):
        return "image/jpeg"
    if ext == "png":
        return "image/png"
    return "application/octet-stream"


def extract_invoice_data(file_bytes: bytes, mime_type: str = "application/pdf") -> dict:
    """Extract invoice fields using Google Document AI.

    Returns dict with: invoice_number, total_cents, confidence.
    """
    if mime_type not in SUPPORTED_MIME_TYPES:
        logger.warning("document_ai_unsupported_mime", mime_type=mime_type)
        return {}

    if not settings.DOCUMENT_AI_PROCESSOR:
        logger.warning("document_ai_not_configured")
        return {}

    client = documentai.DocumentProcessorServiceClient()
    result = client.process_document(
        request=documentai.ProcessRequest(
            name=settings.DOCUMENT_AI_PROCESSOR,
            raw_document=documentai.RawDocument(
                content=file_bytes, mime_type=mime_type
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
        mime_type=mime_type,
    )
    return fields
