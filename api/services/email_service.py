from typing import List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
import logging
import structlog

from api.config import settings

logger = structlog.get_logger()
_std_logger = logging.getLogger(__name__)

MAILTRAP_API_URL = "https://send.api.mailtrap.io/api/send"

# Module-level singleton — reuses TLS connections across calls
_http_client: Optional[httpx.AsyncClient] = None

def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
        )
    return _http_client

class _MailtrapRetryableError(Exception):
    """Raised for 5xx or network errors that warrant a retry."""

@retry(
    retry=retry_if_exception_type(_MailtrapRetryableError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    before_sleep=before_sleep_log(_std_logger, logging.WARNING),
    reraise=False,
)
async def _send_with_retry(
    headers: dict,
    payload: dict,
    to_emails: List[str],
    subject: str,
) -> bool:
    client = get_http_client()
    
    inbox_id = getattr(settings, "MAILTRAP_INBOX_ID", None)
    if inbox_id:
        url = f"https://sandbox.api.mailtrap.io/api/send/{inbox_id}"
    else:
        url = MAILTRAP_API_URL
        
    try:
        response = await client.post(url, headers=headers, json=payload)
    except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
        logger.warning("email_network_error_retrying", error=str(exc), to=to_emails)
        raise _MailtrapRetryableError(str(exc)) from exc

    if response.status_code in (200, 201, 202):
        logger.info(
            "email_sent_mailtrap",
            to=to_emails,
            subject=subject,
        )
        return True

    if response.status_code >= 500:
        logger.warning(
            "email_mailtrap_5xx_retrying",
            status_code=response.status_code,
            to=to_emails,
        )
        raise _MailtrapRetryableError(f"Mailtrap returned {response.status_code}")

    # 4xx — client error, no point retrying (like unverified domain)
    logger.error(
        "email_failed_mailtrap",
        status_code=response.status_code,
        response=response.text[:500],
        to=to_emails,
        subject=subject,
    )
    return False


async def send_email(
    to_emails: List[str],
    subject: str,
    html_content: str,
    sender_name: str = settings.APP_NAME,
    sender_email: str = settings.EMAIL_FROM_ADDRESS,
) -> bool:
    """
    Send email using Mailtrap REST API.
    """
    if not settings.MAILTRAP_API_KEY:
        logger.warning("mailtrap_api_key_missing", message="Email sending skipped")
        return False

    if not to_emails:
        logger.warning("email_no_recipients")
        return False

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {settings.MAILTRAP_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "from": {"name": sender_name, "email": sender_email},
        "to": [{"email": email} for email in to_emails],
        "subject": subject,
        "html": html_content,
    }

    try:
        return await _send_with_retry(headers, payload, to_emails, subject) or False
    except Exception as exc:
        logger.error(
            "email_all_retries_exhausted",
            error=str(exc),
            to=to_emails,
            subject=subject,
        )
        return False
