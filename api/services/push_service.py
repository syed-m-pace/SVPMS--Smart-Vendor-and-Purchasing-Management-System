from __future__ import annotations
# api/services/push_service.py
"""
Firebase Cloud Messaging push notifications.
Sends multicast push to user devices via Firebase Admin SDK.
"""

import asyncio
import logging
from typing import Optional

from firebase_admin import messaging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import structlog

from api.models.user_device import UserDevice

logger = structlog.get_logger()
_std_logger = logging.getLogger(__name__)


class _FCMTransientError(Exception):
    """Wraps transient Firebase errors that are safe to retry."""


@retry(
    retry=retry_if_exception_type(_FCMTransientError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    before_sleep=before_sleep_log(_std_logger, logging.WARNING),
    reraise=False,
)
async def _multicast_with_retry(
    message: messaging.MulticastMessage,
    devices: list,
    session: AsyncSession,
) -> None:
    loop = asyncio.get_event_loop()
    try:
        response = await loop.run_in_executor(
            None, messaging.send_each_for_multicast, message
        )
    except messaging.FirebaseError as exc:
        # Distinguish retryable (quota / server) from permanent errors
        if getattr(exc, "http_response", None) and exc.http_response.status_code >= 500:
            logger.warning("push_fcm_5xx_retrying", error=str(exc))
            raise _FCMTransientError(str(exc)) from exc
        logger.error("push_fcm_permanent_error", error=str(exc))
        return
    except Exception as exc:
        logger.warning("push_fcm_unknown_error_retrying", error=str(exc))
        raise _FCMTransientError(str(exc)) from exc

    logger.info(
        "push_sent",
        success=response.success_count,
        failure=response.failure_count,
        total=len(devices),
    )

    # Clean up unregistered / mismatched tokens
    if response.failure_count > 0:
        for idx, send_response in enumerate(response.responses):
            if send_response.exception and isinstance(
                send_response.exception,
                (messaging.UnregisteredError, messaging.SenderIdMismatchError),
            ):
                device_id = devices[idx].id
                device = await session.get(UserDevice, device_id)
                if device:
                    device.is_active = False
                    logger.info(
                        "push_token_deactivated",
                        device_id=str(device_id),
                        reason=type(send_response.exception).__name__,
                    )


async def send_push(
    session: AsyncSession,
    user_ids: list[str],
    title: str,
    body: str,
    data: Optional[dict] = None,
) -> None:
    """
    Send FCM push notification to all active devices of specified users.

    Retries up to 3 times on transient Firebase server errors.

    Args:
        session: DB session (tenant context should already be set)
        user_ids: List of user UUIDs to notify
        title: Notification title
        body: Notification body text
        data: Optional data payload (key-value strings)
    """
    if not user_ids:
        return

    # Fetch active device tokens for users
    result = await session.execute(
        select(UserDevice.fcm_token, UserDevice.id).where(
            UserDevice.user_id.in_(user_ids),
            UserDevice.is_active == True,  # noqa: E712
        )
    )
    devices = result.all()

    if not devices:
        logger.info("push_no_devices", user_ids=user_ids)
        return

    tokens = [d.fcm_token for d in devices]

    notification = messaging.Notification(title=title, body=body)
    message = messaging.MulticastMessage(
        notification=notification,
        data=data or {},
        tokens=tokens,
    )

    try:
        await _multicast_with_retry(message, devices, session)
    except Exception as exc:
        logger.error(
            "push_all_retries_exhausted",
            error=str(exc),
            user_ids=user_ids,
        )
