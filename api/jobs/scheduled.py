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

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.database import get_db
from api.models.approval import Approval
from api.models.budget import Budget, BudgetReservation
from api.models.department import Department
from api.models.user import User
from api.models.user_device import UserDevice
from api.models.vendor import Vendor, VendorDocument
from api.services.notification_service import send_notification
from api.services.risk_score_service import compute_vendor_risk_score

logger = structlog.get_logger()
router = APIRouter()


async def _require_internal_auth(request: Request):
    """
    Verify request comes from Cloud Scheduler or internal service.
    Validates X-Internal-Secret header against INTERNAL_JOB_SECRET from settings.
    """
    from api.config import settings
    secret = settings.INTERNAL_JOB_SECRET
    if not secret:
        # In development (DEBUG=True), allow unauthenticated internal calls
        if settings.DEBUG:
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="INTERNAL_JOB_SECRET is not configured",
        )
    provided = request.headers.get("X-Internal-Secret")
    if not provided or provided != secret:
        logger.warning("internal_auth_failed", path=request.url.path)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )


@router.post("/check-document-expiry")
async def check_document_expiry(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(_require_internal_auth),
):
    """Daily: Check vendor documents nearing expiry and notify at 30, 14, 7, 3 day thresholds."""
    today = date.today()
    expiry_cutoff = today + timedelta(days=30)
    escalation_thresholds = {30, 14, 7, 3}

    # Join with Vendor to get contact email and name in a single query
    result = await db.execute(
        select(VendorDocument, Vendor.email, Vendor.legal_name)
        .join(Vendor, VendorDocument.vendor_id == Vendor.id)
        .where(
            VendorDocument.expiry_date.between(today, expiry_cutoff),
            Vendor.deleted_at == None,  # noqa: E711
            Vendor.status == "ACTIVE",
        )
    )
    rows = result.all()

    count = 0
    for doc, vendor_email, vendor_name in rows:
        days_remaining = (doc.expiry_date - today).days
        # Only send on escalation threshold days (30, 14, 7, 3)
        if days_remaining not in escalation_thresholds:
            continue
        logger.info(
            "document_expiring",
            vendor_id=str(doc.vendor_id),
            document_type=doc.document_type,
            days_remaining=days_remaining,
        )
        urgency = "URGENT" if days_remaining <= 7 else "WARNING"
        background_tasks.add_task(
            send_notification,
            "document_expiry",
            [vendor_email],
            {
                "vendor_name": vendor_name,
                "document_type": doc.document_type,
                "days_remaining": days_remaining,
                "expiry_date": doc.expiry_date.strftime("%Y-%m-%d"),
                "urgency": urgency,
            },
        )
        count += 1

    logger.info("document_expiry_check_complete", expiring_count=count)
    return {"processed": count}


@router.post("/check-approval-timeouts")
async def check_approval_timeouts(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(_require_internal_auth),
):
    """Every 4 hours: Send reminders for approvals pending > 48h."""
    cutoff = datetime.utcnow() - timedelta(hours=48)

    # Join with User to get approver contact details
    result = await db.execute(
        select(
            Approval,
            User.email,
            User.first_name,
            User.last_name,
        )
        .join(User, Approval.approver_id == User.id)
        .where(
            Approval.status == "PENDING",
            Approval.created_at < cutoff,
        )
    )
    rows = result.all()

    count = 0
    for approval, approver_email, first_name, last_name in rows:
        hours_pending = (datetime.utcnow() - approval.created_at).total_seconds() / 3600
        approver_name = f"{first_name or ''} {last_name or ''}".strip() or approver_email

        logger.warning(
            "approval_timeout",
            approval_id=str(approval.id),
            entity_type=approval.entity_type,
            entity_id=str(approval.entity_id),
            approver_email=approver_email,
            hours_pending=round(hours_pending, 1),
        )

        background_tasks.add_task(
            send_notification,
            "approval_timeout",
            [approver_email],
            {
                "approver_name": approver_name,
                "entity_type": approval.entity_type,
                "entity_ref": str(approval.entity_id),
                "approval_level": approval.approval_level,
                "hours_pending": round(hours_pending, 1),
            },
        )
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

        alert_level = None
        if utilization >= 0.95:
            alerts["critical_95"] += 1
            alert_level = "CRITICAL"
            logger.warning(
                "budget_near_exhaustion",
                budget_id=str(budget.id),
                utilization_pct=round(utilization * 100, 1),
            )
        elif utilization >= 0.80:
            alerts["warning_80"] += 1
            alert_level = "WARNING"
            logger.info(
                "budget_threshold_warning",
                budget_id=str(budget.id),
                utilization_pct=round(utilization * 100, 1),
            )

        # Send email notification to department manager + finance roles
        if alert_level:
            notify_emails = []
            # Get department manager email
            dept_result = await db.execute(
                select(Department, User.email)
                .join(User, Department.manager_id == User.id, isouter=True)
                .where(Department.id == budget.department_id)
            )
            dept_row = dept_result.one_or_none()
            if dept_row and dept_row[1]:
                notify_emails.append(dept_row[1])

            # Get finance_head email
            finance_result = await db.execute(
                select(User.email).where(
                    User.tenant_id == budget.tenant_id,
                    User.role == "finance_head",
                    User.is_active == True,  # noqa: E712
                )
            )
            for row in finance_result.all():
                if row[0] and row[0] not in notify_emails:
                    notify_emails.append(row[0])

            if notify_emails:
                background_tasks.add_task(
                    send_notification,
                    "budget_alert",
                    notify_emails,
                    {
                        "budget_name": budget.name if hasattr(budget, "name") else str(budget.id),
                        "alert_level": alert_level,
                        "utilization_pct": round(utilization * 100, 1),
                        "spent_cents": budget.spent_cents,
                        "total_cents": budget.total_cents,
                    },
                )

    logger.info("budget_alert_check_complete", alerts=alerts)
    return {"checked": len(budgets), "alerts": alerts}


@router.post("/cleanup-fcm-tokens")
async def cleanup_stale_fcm_tokens(
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(_require_internal_auth),
):
    """
    Weekly: Deactivate FCM device tokens that have been inactive for > 30 days.
    Firebase removes stale tokens automatically; this job mirrors that cleanup in our DB
    to prevent accumulating dead registrations that waste push broadcast budget.
    """
    cutoff = datetime.utcnow() - timedelta(days=30)

    # Find stale active tokens: is_active=True but updated_at older than cutoff
    result = await db.execute(
        select(UserDevice).where(
            UserDevice.is_active == True,  # noqa: E712
            UserDevice.updated_at < cutoff,
        )
    )
    stale_devices = result.scalars().all()

    deactivated = 0
    for device in stale_devices:
        device.is_active = False
        deactivated += 1

    if deactivated:
        await db.flush()

    logger.info("fcm_token_cleanup_complete", deactivated=deactivated)
    return {"deactivated": deactivated}


@router.post("/refresh-vendor-risk-scores")
async def refresh_all_vendor_risk_scores(
    db: AsyncSession = Depends(get_db),
    _auth: None = Depends(_require_internal_auth),
):
    """
    Weekly: Recompute risk scores for all active vendors in the system.
    Runs across all tenants (uses superuser DB session without tenant filter).
    """
    result = await db.execute(
        select(Vendor.id).where(
            Vendor.deleted_at.is_(None),
            Vendor.status == "ACTIVE",
        )
    )
    vendor_ids = [str(row[0]) for row in result.all()]

    updated = 0
    errors = 0
    for vendor_id in vendor_ids:
        try:
            score = await compute_vendor_risk_score(db, vendor_id)
            if score is not None:
                updated += 1
        except Exception as e:
            logger.error("risk_score_refresh_failed", vendor_id=vendor_id, error=str(e))
            errors += 1

    logger.info("vendor_risk_score_refresh_complete", updated=updated, errors=errors)
    return {"updated": updated, "errors": errors}
