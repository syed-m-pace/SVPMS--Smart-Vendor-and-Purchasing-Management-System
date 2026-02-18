"""
Notification service — template rendering + dispatch via email.

Emails are resolved DURING the request (while DB session is open),
then dispatched via BackgroundTasks (fire-and-forget).
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.models.user import User
from api.services.email_service import send_email

logger = structlog.get_logger()

# ---------- Template registry ----------

TEMPLATES = {
    "pr_approval_request": {
        "subject": "[SVPMS] Purchase Request {pr_number} — Your Approval Required",
        "html": (
            "<h2>Approval Required</h2>"
            "<p>A purchase request <strong>{pr_number}</strong> requires your approval.</p>"
            "<p><strong>Description:</strong> {description}</p>"
            "<p><strong>Amount:</strong> {currency} {amount_display}</p>"
            "<p><strong>Requester:</strong> {requester_email}</p>"
            "<p>Please log in to SVPMS to review and approve or reject.</p>"
        ),
    },
    "pr_approved": {
        "subject": "[SVPMS] Purchase Request {pr_number} — Approved",
        "html": (
            "<h2>Purchase Request Approved</h2>"
            "<p>Your purchase request <strong>{pr_number}</strong> has been "
            "<span style='color:green'>approved</span>.</p>"
            "<p><strong>Amount:</strong> {currency} {amount_display}</p>"
            "<p>A purchase order can now be created.</p>"
        ),
    },
    "pr_rejected": {
        "subject": "[SVPMS] Purchase Request {pr_number} — Rejected",
        "html": (
            "<h2>Purchase Request Rejected</h2>"
            "<p>Your purchase request <strong>{pr_number}</strong> has been "
            "<span style='color:red'>rejected</span>.</p>"
            "<p><strong>Reason:</strong> {reason}</p>"
        ),
    },
    "po_issued": {
        "subject": "[SVPMS] Purchase Order {po_number} — Issued",
        "html": (
            "<h2>Purchase Order Issued</h2>"
            "<p>Purchase order <strong>{po_number}</strong> has been issued to vendor.</p>"
            "<p><strong>Amount:</strong> {currency} {amount_display}</p>"
        ),
    },
    "invoice_exception": {
        "subject": "[SVPMS] Invoice {invoice_number} — Exception",
        "html": (
            "<h2>Invoice Exception</h2>"
            "<p>Invoice <strong>{invoice_number}</strong> has a matching exception "
            "and requires review.</p>"
        ),
    },
}


def _format_amount(cents: int) -> str:
    """Convert cents to display string (e.g. 500000 → '5,000.00')."""
    return f"{cents / 100:,.2f}"


async def resolve_user_emails(
    session: AsyncSession, user_ids: list[str]
) -> list[str]:
    """Batch look up emails for user IDs. Returns list of emails."""
    if not user_ids:
        return []
    result = await session.execute(
        select(User.email).where(User.id.in_(user_ids))
    )
    return [row[0] for row in result.all()]


async def send_notification(
    template_id: str,
    recipient_emails: list[str],
    context: dict,
    session: Optional[AsyncSession] = None,
    recipient_user_ids: Optional[list[str]] = None,
) -> bool:
    """
    Render template and dispatch email.

    If recipient_user_ids provided and session available, resolves emails.
    Otherwise uses recipient_emails directly.
    """
    template = TEMPLATES.get(template_id)
    if not template:
        logger.warning("notification_template_not_found", template_id=template_id)
        return False

    # Resolve user IDs to emails if needed
    emails = list(recipient_emails) if recipient_emails else []
    if recipient_user_ids and session:
        resolved = await resolve_user_emails(session, recipient_user_ids)
        emails.extend(resolved)

    if not emails:
        logger.warning("notification_no_recipients", template_id=template_id)
        return False

    # Add amount_display helper to context
    if "amount_cents" in context and "amount_display" not in context:
        context["amount_display"] = _format_amount(context["amount_cents"])

    try:
        subject = template["subject"].format(**context)
        html = template["html"].format(**context)
    except KeyError as e:
        logger.error("notification_template_render_error", template_id=template_id, missing_key=str(e))
        return False

    result = await send_email(emails, subject, html)

    logger.info(
        "notification_sent",
        template_id=template_id,
        recipients=emails,
        success=result,
    )
    return result
