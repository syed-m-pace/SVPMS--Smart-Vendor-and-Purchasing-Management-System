import csv
import io
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
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
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    actor_id: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
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
    if from_date:
        from_dt = datetime.combine(from_date, datetime.min.time())
        q = q.where(AuditLog.created_at >= from_dt)
        count_q = count_q.where(AuditLog.created_at >= from_dt)
    if to_date:
        to_dt = datetime.combine(to_date, datetime.max.time())
        q = q.where(AuditLog.created_at <= to_dt)
        count_q = count_q.where(AuditLog.created_at <= to_dt)

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


@router.get("/export")
async def export_audit_logs(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    actor_id: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("admin", "finance_head", "cfo")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    """Export audit logs as CSV. Max 10,000 rows."""
    q = select(AuditLog)

    if entity_type:
        q = q.where(AuditLog.entity_type == entity_type)
    if entity_id:
        q = q.where(AuditLog.entity_id == entity_id)
    if actor_id:
        q = q.where(AuditLog.actor_id == actor_id)
    if from_date:
        q = q.where(AuditLog.created_at >= datetime.combine(from_date, datetime.min.time()))
    if to_date:
        q = q.where(AuditLog.created_at <= datetime.combine(to_date, datetime.max.time()))

    result = await db.execute(
        q.order_by(AuditLog.created_at.desc()).limit(10_000)
    )
    logs = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "actor_email", "action", "entity_type", "entity_id",
        "before_state", "after_state", "created_at",
    ])
    for log in logs:
        writer.writerow([
            str(log.id),
            log.actor_email or "",
            log.action,
            log.entity_type,
            str(log.entity_id),
            str(log.before_state) if log.before_state else "",
            str(log.after_state) if log.after_state else "",
            log.created_at.isoformat() if log.created_at else "",
        ])

    csv_content = output.getvalue()
    filename = f"audit_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
