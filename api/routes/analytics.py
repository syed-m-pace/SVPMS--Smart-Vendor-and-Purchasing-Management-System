"""
Spend analytics API — /api/v1/analytics/spend

Provides:
  - spend by department (budget actual vs. total)
  - spend by vendor (PO total_cents grouped)
  - spend by status category (PR pipeline counts)
  - budget vs. actual trend (current quarter)
  - monthly invoice spend trend (last 6 months)
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.auth import get_current_user
from api.middleware.tenant import get_db_with_tenant
from api.middleware.authorization import require_roles
from api.models.budget import Budget
from api.models.department import Department
from api.models.invoice import Invoice
from api.models.purchase_order import PurchaseOrder
from api.models.purchase_request import PurchaseRequest
from api.models.vendor import Vendor
from api.services.budget_service import get_current_fiscal_period

router = APIRouter()

_PRIVILEGED_ROLES = {
    "admin", "finance_head", "cfo", "procurement", "procurement_lead", "finance"
}


@router.get("/spend")
async def get_spend_analytics(
    fiscal_year: Optional[int] = Query(None),
    quarter: Optional[int] = Query(None, ge=1, le=4),
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(
        require_roles(
            "admin", "finance_head", "cfo", "procurement",
            "procurement_lead", "finance", "manager",
        )
    ),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    """
    Returns spend analytics scoped to role:
    - Privileged roles: all tenant data
    - Manager: scoped to their department
    """
    user_role = current_user.get("role")
    department_id = current_user.get("department_id")
    is_privileged = user_role in _PRIVILEGED_ROLES

    fy, q = get_current_fiscal_period()
    if fiscal_year:
        fy = fiscal_year
    if quarter:
        q = quarter

    # ── 1. Spend by Department (from budgets) ───────────────────────────────
    dept_q = (
        select(
            Budget.department_id,
            Department.name.label("department_name"),
            func.coalesce(func.sum(Budget.total_cents), 0).label("total_budget"),
            func.coalesce(func.sum(Budget.spent_cents), 0).label("spent"),
            func.coalesce(func.sum(Budget.reserved_cents), 0).label("reserved"),
        )
        .join(Department, Budget.department_id == Department.id, isouter=True)
        .where(Budget.fiscal_year == fy, Budget.quarter == q)
        .group_by(Budget.department_id, Department.name)
    )
    if not is_privileged and department_id:
        dept_q = dept_q.where(Budget.department_id == department_id)

    # ── 2. Spend by Vendor (from POs) ───────────────────────────────────────
    vendor_q = (
        select(
            PurchaseOrder.vendor_id,
            Vendor.legal_name.label("vendor_name"),
            func.coalesce(func.sum(PurchaseOrder.total_cents), 0).label("total_spent"),
            func.count(PurchaseOrder.id).label("po_count"),
        )
        .join(Vendor, PurchaseOrder.vendor_id == Vendor.id, isouter=True)
        .where(
            PurchaseOrder.status.notin_(["DRAFT", "CANCELLED"]),
            PurchaseOrder.deleted_at.is_(None),
        )
        .group_by(PurchaseOrder.vendor_id, Vendor.legal_name)
        .order_by(func.sum(PurchaseOrder.total_cents).desc())
        .limit(10)
    )
    if not is_privileged and department_id:
        vendor_q = vendor_q.join(
            PurchaseRequest,
            PurchaseOrder.pr_id == PurchaseRequest.id,
            isouter=True,
        ).where(PurchaseRequest.department_id == department_id)

    # ── 3. PR Pipeline by Status ─────────────────────────────────────────────
    pr_status_q = (
        select(
            PurchaseRequest.status,
            func.count(PurchaseRequest.id).label("count"),
        )
        .where(PurchaseRequest.deleted_at.is_(None))
        .group_by(PurchaseRequest.status)
    )
    if not is_privileged and department_id:
        pr_status_q = pr_status_q.where(
            PurchaseRequest.department_id == department_id
        )

    # ── 4. Monthly Invoice Spend (last 6 months) ────────────────────────────
    six_months_ago = datetime.utcnow() - timedelta(days=182)
    monthly_q = (
        select(
            extract("year", Invoice.created_at).label("year"),
            extract("month", Invoice.created_at).label("month"),
            func.coalesce(func.sum(Invoice.total_cents), 0).label("total_cents"),
            func.count(Invoice.id).label("invoice_count"),
        )
        .where(
            Invoice.status.notin_(["UPLOADED"]),
            Invoice.created_at >= six_months_ago,
        )
        .group_by(
            extract("year", Invoice.created_at),
            extract("month", Invoice.created_at),
        )
        .order_by(
            extract("year", Invoice.created_at),
            extract("month", Invoice.created_at),
        )
    )

    # ── Execute all queries concurrently ────────────────────────────────────
    dept_res, vendor_res, pr_res, monthly_res = await asyncio.gather(
        db.execute(dept_q),
        db.execute(vendor_q),
        db.execute(pr_status_q),
        db.execute(monthly_q),
    )

    # ── Build response payload ───────────────────────────────────────────────
    dept_rows = dept_res.all()
    spend_by_department = [
        {
            "department_id": str(r.department_id),
            "department_name": r.department_name or "Unknown",
            "total_budget_cents": int(r.total_budget),
            "spent_cents": int(r.spent),
            "reserved_cents": int(r.reserved),
            "available_cents": max(int(r.total_budget) - int(r.spent) - int(r.reserved), 0),
            "utilization_pct": (
                round((int(r.spent) + int(r.reserved)) / int(r.total_budget) * 100, 1)
                if int(r.total_budget) > 0 else 0
            ),
        }
        for r in dept_rows
    ]

    vendor_rows = vendor_res.all()
    spend_by_vendor = [
        {
            "vendor_id": str(r.vendor_id),
            "vendor_name": r.vendor_name or "Unknown",
            "total_spent_cents": int(r.total_spent),
            "po_count": int(r.po_count),
        }
        for r in vendor_rows
    ]

    pr_rows = pr_res.all()
    pr_pipeline = {r.status: int(r.count) for r in pr_rows}

    monthly_rows = monthly_res.all()
    monthly_trend = [
        {
            "year": int(r.year),
            "month": int(r.month),
            "label": datetime(int(r.year), int(r.month), 1).strftime("%b %Y"),
            "total_cents": int(r.total_cents),
            "invoice_count": int(r.invoice_count),
        }
        for r in monthly_rows
    ]

    # ── Summary totals ────────────────────────────────────────────────────────
    total_budget = sum(d["total_budget_cents"] for d in spend_by_department)
    total_spent = sum(d["spent_cents"] for d in spend_by_department)
    total_reserved = sum(d["reserved_cents"] for d in spend_by_department)
    total_po_spend = sum(v["total_spent_cents"] for v in spend_by_vendor)

    return {
        "fiscal_year": fy,
        "quarter": q,
        "summary": {
            "total_budget_cents": total_budget,
            "total_spent_cents": total_spent,
            "total_reserved_cents": total_reserved,
            "available_cents": max(total_budget - total_spent - total_reserved, 0),
            "budget_utilization_pct": (
                round((total_spent + total_reserved) / total_budget * 100, 1)
                if total_budget > 0 else 0
            ),
            "total_po_spend_cents": total_po_spend,
        },
        "spend_by_department": spend_by_department,
        "spend_by_vendor": spend_by_vendor,
        "pr_pipeline": pr_pipeline,
        "monthly_invoice_trend": monthly_trend,
    }
