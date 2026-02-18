from __future__ import annotations
# api/routes/devices.py
"""
Device token registration for FCM push notifications.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.middleware.auth import get_current_user
from api.middleware.tenant import get_db_with_tenant
from api.models.user_device import UserDevice

logger = structlog.get_logger()
router = APIRouter()


class DeviceRegisterRequest(BaseModel):
    fcm_token: str
    device_type: str  # android, ios, web
    device_name: Optional[str] = None


class DeviceResponse(BaseModel):
    id: str
    fcm_token: str
    device_type: str
    device_name: Optional[str]
    is_active: bool
    registered_at: str


def _to_response(d: UserDevice) -> DeviceResponse:
    return DeviceResponse(
        id=str(d.id),
        fcm_token=d.fcm_token,
        device_type=d.device_type,
        device_name=d.device_name,
        is_active=d.is_active,
        registered_at=d.registered_at.isoformat() if d.registered_at else "",
    )


@router.get("", response_model=list[DeviceResponse])
async def list_devices(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    """List all registered devices for the current user."""
    result = await db.execute(
        select(UserDevice).where(
            UserDevice.user_id == current_user["user_id"],
            UserDevice.is_active == True,  # noqa: E712
        )
    )
    devices = result.scalars().all()
    return [_to_response(d) for d in devices]


@router.post("", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def register_device(
    body: DeviceRegisterRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    """Register or re-activate an FCM device token."""
    if body.device_type not in ("android", "ios", "web"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="device_type must be one of: android, ios, web",
        )

    # Check if token already registered for this user
    existing = await db.execute(
        select(UserDevice).where(
            UserDevice.user_id == current_user["user_id"],
            UserDevice.fcm_token == body.fcm_token,
        )
    )
    device = existing.scalar_one_or_none()

    if device:
        # Re-activate existing device
        device.is_active = True
        device.device_name = body.device_name or device.device_name
        device.device_type = body.device_type
        await db.flush()
        logger.info("device_reactivated", device_id=str(device.id))
        return _to_response(device)

    # Create new device registration
    device = UserDevice(
        user_id=current_user["user_id"],
        tenant_id=current_user["tenant_id"],
        fcm_token=body.fcm_token,
        device_type=body.device_type,
        device_name=body.device_name,
    )
    db.add(device)
    await db.flush()
    logger.info("device_registered", device_id=str(device.id), device_type=body.device_type)
    return _to_response(device)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deregister_device(
    device_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    """Deregister (deactivate) a device token."""
    result = await db.execute(
        select(UserDevice).where(
            UserDevice.id == device_id,
            UserDevice.user_id == current_user["user_id"],
        )
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    device.is_active = False
    await db.flush()
    logger.info("device_deregistered", device_id=device_id)
