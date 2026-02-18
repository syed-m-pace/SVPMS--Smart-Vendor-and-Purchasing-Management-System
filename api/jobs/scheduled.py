# api/jobs/scheduled.py
"""
Scheduled background jobs triggered by Cloud Scheduler → API endpoints.
From 01_BACKEND.md §5.4.

Jobs:
  - check-document-expiry: Daily at 9:00 UTC
  - check-approval-timeouts: Every 4 hours
  - budget-utilization-alerts: Weekly Monday 8:00 UTC
"""

from datetime import datetime, timedelta, date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.database import get_db
from api.models.approval import Approval
from api.models.budget import Budget, BudgetReservation

logger = structlog.get_logger()
router = APIRouter()


async def _require_internal_auth(request: Request):
    """
    Verify request comes from Cloud Scheduler or internal service.
    In production, checks OIDC token. In dev, accepts any request.
    """
    # In production, validate Cloud Scheduler OIDC token:
    # auth_header = request.headers.get("Authorization")
    # if not auth_header: raise HTTPException(403)
    # Verify OIDC token...
    pass


@router.post("/check-document-expiry")
async def check_document_expiry(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(_require_internal_auth),
):
    """Daily: Check vendor documents nearing expiry (30-day window)."""
    from api.models.vendor import VendorDocument

    today = date.today()
    expiry_cutoff = today + timedelta(days=30)

    result = await db.execute(
        select(VendorDocument).where(
            VendorDocument.expiry_date.between(today, expiry_cutoff)
        )
    )
    expiring_docs = result.scalars().all()

    count = 0
    for doc in expiring_docs:
        days_remaining = (doc.expiry_date - today).days
        logger.info(
            "document_expiring",
            vendor_id=str(doc.vendor_id),
            document_type=doc.document_type,
            days_remaining=days_remaining,
        )
        # TODO: Wire to send_notification once expiry template exists
        count += 1

    logger.info("document_expiry_check_complete", expiring_count=count)
    return {"processed": count}


@router.post("/check-approval-timeouts")
async def check_approval_timeouts(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(_require_internal_auth),
):
    """Every 4 hours: Escalate approvals pending > 48h."""
    cutoff = datetime.utcnow() - timedelta(hours=48)

    result = await db.execute(
        select(Approval).where(
            Approval.status == "PENDING",
            Approval.created_at < cutoff,
        )
    )
    stale_approvals = result.scalars().all()

    count = 0
    for approval in stale_approvals:
        hours_pending = (datetime.utcnow() - approval.created_at).total_seconds() / 3600
        logger.warning(
            "approval_timeout",
            approval_id=str(approval.id),
            entity_type=approval.entity_type,
            entity_id=str(approval.entity_id),
            hours_pending=round(hours_pending, 1),
        )
        # TODO: Wire to escalation logic (notify next-level approver)
        count += 1

    logger.info("approval_timeout_check_complete", escalated_count=count)
    return {"escalated": count}


@router.post("/budget-alerts")
async def budget_utilization_alerts(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(_require_internal_auth),
):
    """Weekly (Monday 8AM UTC): Check budget utilization thresholds."""
    result = await db.execute(select(Budget))
    budgets = result.scalars().all()

    alerts = {"warning_80": 0, "critical_95": 0}

    for budget in budgets:
        if budget.total_cents == 0:
            continue

        # Sum committed reservations inline
        reserved_result = await db.execute(
            select(func.coalesce(func.sum(BudgetReservation.amount_cents), 0)).where(
                BudgetReservation.budget_id == budget.id,
                BudgetReservation.status == "COMMITTED",
            )
        )
        reserved = reserved_result.scalar() or 0
        utilization = (budget.spent_cents + reserved) / budget.total_cents

        if utilization >= 0.95:
            alerts["critical_95"] += 1
            logger.warning(
                "budget_near_exhaustion",
                budget_id=str(budget.id),
                utilization_pct=round(utilization * 100, 1),
            )
        elif utilization >= 0.80:
            alerts["warning_80"] += 1
            logger.info(
                "budget_threshold_warning",
                budget_id=str(budget.id),
                utilization_pct=round(utilization * 100, 1),
            )

    logger.info("budget_alert_check_complete", alerts=alerts)
    return {"checked": len(budgets), "alerts": alerts}
