from __future__ import annotations
# api/services/push_service.py
"""
Firebase Cloud Messaging push notifications.
Sends multicast push to user devices via Firebase Admin SDK.
"""

from typing import Optional

from firebase_admin import messaging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.models.user_device import UserDevice

logger = structlog.get_logger()


async def send_push(
    session: AsyncSession,
    user_ids: list[str],
    title: str,
    body: str,
    data: Optional[dict] = None,
):
    """
    Send FCM push notification to all active devices of specified users.

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
        response = messaging.send_each_for_multicast(message)
        logger.info(
            "push_sent",
            success=response.success_count,
            failure=response.failure_count,
            total=len(tokens),
        )

        # Clean up unregistered tokens
        if response.failure_count > 0:
            for idx, send_response in enumerate(response.responses):
                if (
                    send_response.exception
                    and isinstance(
                        send_response.exception,
                        (
                            messaging.UnregisteredError,
                            messaging.SenderIdMismatchError,
                        ),
                    )
                ):
                    # Deactivate stale device
                    device_id = devices[idx].id
                    device = await session.get(UserDevice, device_id)
                    if device:
                        device.is_active = False
                        logger.info(
                            "push_token_deactivated",
                            device_id=str(device_id),
                            reason=type(send_response.exception).__name__,
                        )

    except Exception as e:
        logger.error("push_failed", error=str(e), user_ids=user_ids)
