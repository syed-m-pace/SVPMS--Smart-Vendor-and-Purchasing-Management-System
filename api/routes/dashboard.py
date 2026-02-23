import asyncio
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.auth import get_current_user
from api.middleware.tenant import get_db_with_tenant
from api.models.purchase_order import PurchaseOrder
from api.models.invoice import Invoice
from api.models.budget import Budget
from api.models.rfq import RFQ
from api.services.budget_service import get_current_fiscal_period

router = APIRouter()

@router.get("/stats")
async def get_dashboard_stats(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    user_role = current_user.get("role")
    user_id = current_user.get("user_id")
    department_id = current_user.get("department_id")

    # 1. Pending PRs count
    pr_q = select(func.count(PurchaseRequest.id)).where(
        PurchaseRequest.status == "PENDING",
        PurchaseRequest.deleted_at == None
    )
    
    privileged_roles = ["admin", "manager", "finance_head", "cfo", "procurement", "viewer"]
    if user_role not in privileged_roles:
        pr_q = pr_q.where(PurchaseRequest.requester_id == user_id)
    elif user_role == "manager" and department_id:
        pr_q = pr_q.where(
            or_(
                PurchaseRequest.department_id == department_id,
                PurchaseRequest.requester_id == user_id
            )
        )

    # 2. Active POs count (Issued, Acknowledged, Partially Received)
    po_q = select(func.count(PurchaseOrder.id)).where(
        PurchaseOrder.status.in_(["ISSUED", "ACKNOWLEDGED", "PARTIALLY_RECEIVED"])
    )
    
    inv_q = select(func.count(Invoice.id)).where(Invoice.status == "EXCEPTION")
    
    # 3b. Open Invoices count (for mobile)
    open_inv_q = select(func.count(Invoice.id)).where(Invoice.status != "PAID")
    
    # 3c. Pending RFQs count (for mobile)
    rfq_q = select(func.count(RFQ.id)).where(RFQ.status != "CLOSED")

    # 4. Budget Utilization
    fy, q = get_current_fiscal_period()
    budget_q = select(
        func.sum(Budget.total_cents).label("total"),
        func.sum(Budget.spent_cents).label("spent")
    ).where(
        Budget.fiscal_year == fy,
        Budget.quarter == q
    )

    pr_res, po_res, inv_res, open_inv_res, rfq_res, budget_res = await asyncio.gather(
        db.execute(pr_q),
        db.execute(po_q),
        db.execute(inv_q),
        db.execute(open_inv_q),
        db.execute(rfq_q),
        db.execute(budget_q)
    )

    pending_prs = pr_res.scalar() or 0
    active_pos = po_res.scalar() or 0
    invoice_exceptions = inv_res.scalar() or 0
    open_invoices = open_inv_res.scalar() or 0
    pending_rfqs = rfq_res.scalar() or 0
    
    budget_row = budget_res.first()
    total_budget = budget_row.total if budget_row and budget_row.total else 0
    total_spent = budget_row.spent if budget_row and budget_row.spent else 0
    budget_utilization = round((total_spent / total_budget) * 100) if total_budget > 0 else 0

    return {
        "pending_prs": pending_prs,
        "active_pos": active_pos,
        "invoice_exceptions": invoice_exceptions,
        "open_invoices": open_invoices,
        "pending_rfqs": pending_rfqs,
        "budget_utilization": budget_utilization
    }
