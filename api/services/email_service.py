from typing import List, Optional
import httpx
from api.config import settings
import structlog

logger = structlog.get_logger()

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

async def send_email(to_emails: List[str], subject: str, html_content: str, sender_name: str = settings.APP_NAME, sender_email: str = settings.EMAIL_FROM_ADDRESS):
    """
    Send email using Brevo (formerly Sendinblue) API via HTTPX.
    """
    if not settings.BREVO_API_KEY:
        logger.warning("brevo_api_key_missing", message="Email sending skipped")
        return False

    if not to_emails:
        logger.warning("email_no_recipients")
        return False

    headers = {
        "accept": "application/json",
        "api-key": settings.BREVO_API_KEY,
        "content-type": "application/json"
    }

    # Format recipients for Brevo
    to_list = [{"email": email} for email in to_emails]
    
    payload = {
        "sender": {
            "name": sender_name,
            "email": sender_email
        },
        "to": to_list,
        "subject": subject,
        "htmlContent": html_content
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(BREVO_API_URL, headers=headers, json=payload, timeout=10.0)
            
            if response.status_code in (201, 202):
                logger.info("email_sent_brevo", to=to_emails, subject=subject, message_id=response.json().get("messageId"))
                return True
            else:
                logger.error("email_failed_brevo", status_code=response.status_code, response=response.text)
                return False
    except Exception as e:
        logger.error("email_exception_brevo", error=str(e))
        return False
