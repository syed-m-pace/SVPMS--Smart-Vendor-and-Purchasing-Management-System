from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import structlog
from pydantic import BaseModel
from datetime import datetime
import uuid

from api.middleware.auth import get_current_user
from api.middleware.tenant import get_db_with_tenant
from api.models.notification import AppNotification
from api.services.vendor_service import resolve_vendor_for_user

logger = structlog.get_logger()
router = APIRouter()


class NotificationResponse(BaseModel):
    id: str
    title: str
    body: str
    type: str
    entity_id: Optional[str] = None
    is_read: bool = False
    created_at: str
    
    model_config = {"from_attributes": True}


@router.get("", response_model=List[NotificationResponse])
async def list_notifications(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    """Fetch recent notifications for the logged-in user or vendor."""
    q = select(AppNotification)
    
    if current_user["role"] == "vendor":
        vendor = await resolve_vendor_for_user(db, current_user)
        if not vendor:
            return []
        q = q.where(AppNotification.vendor_id == vendor.id)
    else:
        q = q.where(AppNotification.user_id == current_user["user_id"])
        
    q = q.order_by(AppNotification.created_at.desc()).limit(50)
    result = await db.execute(q)
    
    return [
        NotificationResponse(
            id=str(row.id),
            title=row.title,
            body=row.body,
            type=row.type,
            entity_id=row.entity_id,
            is_read=row.is_read,
            created_at=row.created_at.isoformat(),
        )
        for row in result.scalars().all()
    ]


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    """Mark a specific notification as read."""
    q = select(AppNotification).where(AppNotification.id == notification_id)
    
    if current_user["role"] == "vendor":
        vendor = await resolve_vendor_for_user(db, current_user)
        if vendor:
            q = q.where(AppNotification.vendor_id == vendor.id)
    else:
        q = q.where(AppNotification.user_id == current_user["user_id"])
        
    result = await db.execute(q)
    noti = result.scalar_one_or_none()
    
    if not noti:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    noti.is_read = True
    await db.commit()
    
    return NotificationResponse(
        id=str(noti.id),
        title=noti.title,
        body=noti.body,
        type=noti.type,
        entity_id=noti.entity_id,
        is_read=noti.is_read,
        created_at=noti.created_at.isoformat(),
    )
