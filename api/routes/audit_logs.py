from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.auth import get_current_user
from api.middleware.authorization import require_roles
from api.middleware.tenant import get_db_with_tenant
from api.models.audit_log import AuditLog
from api.schemas.audit_log import AuditLogResponse
from api.schemas.common import PaginatedResponse, build_pagination

router = APIRouter()


@router.get("", response_model=PaginatedResponse[AuditLogResponse])
async def list_audit_logs(
    entity_type: str = Query(None),
    entity_id: str = Query(None),
    actor_id: str = Query(None),
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("admin", "finance_head", "cfo", "procurement_lead")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    q = select(AuditLog)
    count_q = select(func.count(AuditLog.id))

    if entity_type:
        q = q.where(AuditLog.entity_type == entity_type)
        count_q = count_q.where(AuditLog.entity_type == entity_type)
    if entity_id:
        q = q.where(AuditLog.entity_id == entity_id)
        count_q = count_q.where(AuditLog.entity_id == entity_id)
    if actor_id:
        q = q.where(AuditLog.actor_id == actor_id)
        count_q = count_q.where(AuditLog.actor_id == actor_id)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        q.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    logs = result.scalars().all()

    items = [
        AuditLogResponse(
            id=str(log.id),
            tenant_id=str(log.tenant_id),
            actor_id=str(log.actor_id) if log.actor_id else None,
            actor_email=log.actor_email,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=str(log.entity_id),
            before_state=log.before_state,
            after_state=log.after_state,
            created_at=log.created_at.isoformat() if log.created_at else "",
        )
        for log in logs
    ]

    return PaginatedResponse(data=items, pagination=build_pagination(page, limit, total))
