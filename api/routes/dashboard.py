import asyncio
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.auth import get_current_user
from api.middleware.tenant import get_db_with_tenant
from api.models.purchase_request import PurchaseRequest
from api.models.purchase_order import PurchaseOrder
from api.models.invoice import Invoice
from api.models.budget import Budget
from api.models.rfq import Rfq, RfqBid
from api.models.vendor import Vendor
from api.services.budget_service import get_current_fiscal_period
from api.services.vendor_service import resolve_vendor_for_user

router = APIRouter()

# Roles that see all tenant-wide data (not scoped to dept or vendor)
_PRIVILEGED_ROLES = {"admin", "finance_head", "cfo", "procurement", "procurement_lead", "finance"}


@router.get("/stats")
async def get_dashboard_stats(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    user_role = current_user.get("role")
    user_id = current_user.get("user_id")
    department_id = current_user.get("department_id")

    # -----------------------------------------------------------------------
    # Determine scope filters based on role
    # -----------------------------------------------------------------------
    is_vendor = user_role == "vendor"
    is_manager = user_role == "manager"
    is_privileged = user_role in _PRIVILEGED_ROLES

    vendor_obj = None
    if is_vendor:
        vendor_obj = await resolve_vendor_for_user(db, current_user)
        if not vendor_obj:
            return {
                "pending_prs": 0,
                "active_pos": 0,
                "invoice_exceptions": 0,
                "open_invoices": 0,
                "pending_rfqs": 0,
                "budget_utilization": 0,
            }

    # -----------------------------------------------------------------------
    # 1. Pending PRs
    # -----------------------------------------------------------------------
    pr_q = select(func.count(PurchaseRequest.id)).where(
        PurchaseRequest.status == "PENDING",
        PurchaseRequest.deleted_at == None  # noqa: E711
    )
    if is_privileged:
        pass  # all tenant PRs
    elif is_manager and department_id:
        pr_q = pr_q.where(
            or_(
                PurchaseRequest.department_id == department_id,
                PurchaseRequest.requester_id == user_id,
            )
        )
    elif is_vendor:
        # Vendors don't submit PRs — return 0
        pr_q = pr_q.where(PurchaseRequest.requester_id == None)  # noqa: E711
    else:
        pr_q = pr_q.where(PurchaseRequest.requester_id == user_id)

    # -----------------------------------------------------------------------
    # 2. Active POs (Issued, Acknowledged, Partially Received)
    # -----------------------------------------------------------------------
    po_q = select(func.count(PurchaseOrder.id)).where(
        PurchaseOrder.status.in_(["ISSUED", "ACKNOWLEDGED", "PARTIALLY_RECEIVED"])
    )
    if is_vendor and vendor_obj:
        po_q = po_q.where(PurchaseOrder.vendor_id == vendor_obj.id)
    elif is_manager and department_id:
        # POs don't have a department_id; scope via the linked PR's department
        po_q = po_q.join(
            PurchaseRequest,
            PurchaseOrder.pr_id == PurchaseRequest.id,
            isouter=True,
        ).where(
            or_(
                PurchaseRequest.department_id == department_id,
                PurchaseOrder.pr_id == None,  # noqa: E711 — RFQ-sourced POs visible to all managers
            )
        )
    # else: privileged → all tenant POs

    # -----------------------------------------------------------------------
    # 3a. Invoice exceptions (finance/admin view)
    # -----------------------------------------------------------------------
    inv_q = select(func.count(Invoice.id)).where(Invoice.status == "EXCEPTION")
    if is_vendor and vendor_obj:
        inv_q = inv_q.where(Invoice.vendor_id == vendor_obj.id)
    elif is_manager:
        # Managers see exceptions for invoices linked to their dept's POs
        inv_q = inv_q.join(PurchaseOrder, Invoice.po_id == PurchaseOrder.id, isouter=True).join(
            PurchaseRequest, PurchaseOrder.pr_id == PurchaseRequest.id, isouter=True
        ).where(
            or_(
                PurchaseRequest.department_id == department_id,
                Invoice.po_id == None,  # noqa: E711
            )
        )

    # -----------------------------------------------------------------------
    # 3b. Open invoices (for mobile vendor view)
    # -----------------------------------------------------------------------
    open_inv_q = select(func.count(Invoice.id)).where(Invoice.status != "PAID")
    if is_vendor and vendor_obj:
        open_inv_q = open_inv_q.where(Invoice.vendor_id == vendor_obj.id)
    elif not is_privileged and not is_manager:
        open_inv_q = open_inv_q.where(Invoice.vendor_id == None)  # noqa: E711 — empty for others

    # -----------------------------------------------------------------------
    # 3c. Pending RFQs
    # -----------------------------------------------------------------------
    rfq_q = select(func.count(Rfq.id)).where(Rfq.status.in_(["OPEN", "DRAFT"]))
    if is_vendor and vendor_obj:
        # Vendor sees RFQs they have been invited to bid on (have a bid row) or OPEN ones
        rfq_q = rfq_q.join(
            RfqBid, RfqBid.rfq_id == Rfq.id, isouter=True
        ).where(
            or_(
                RfqBid.vendor_id == vendor_obj.id,
                Rfq.status == "OPEN",
            )
        ).distinct()

    # -----------------------------------------------------------------------
    # 4. Budget utilization (scoped to dept for managers)
    # -----------------------------------------------------------------------
    fy, q = get_current_fiscal_period()
    budget_q = select(
        func.sum(Budget.total_cents).label("total"),
        func.sum(Budget.spent_cents).label("spent")
    ).where(
        Budget.fiscal_year == fy,
        Budget.quarter == q
    )
    if is_manager and department_id:
        budget_q = budget_q.where(Budget.department_id == department_id)

    # -----------------------------------------------------------------------
    # 5. Invoice status breakdown (for payment chart)
    # -----------------------------------------------------------------------
    inv_status_q = (
        select(
            Invoice.status,
            func.count(Invoice.id).label("count"),
        )
        .group_by(Invoice.status)
    )
    if is_vendor and vendor_obj:
        inv_status_q = inv_status_q.where(Invoice.vendor_id == vendor_obj.id)
    elif is_manager and department_id:
        inv_status_q = (
            inv_status_q
            .join(PurchaseOrder, Invoice.po_id == PurchaseOrder.id, isouter=True)
            .join(PurchaseRequest, PurchaseOrder.pr_id == PurchaseRequest.id, isouter=True)
            .where(
                or_(
                    PurchaseRequest.department_id == department_id,
                    Invoice.po_id == None,  # noqa: E711
                )
            )
        )

    # -----------------------------------------------------------------------
    # 6. Total vendors count
    # -----------------------------------------------------------------------
    vendor_count_q = select(func.count(Vendor.id)).where(
        Vendor.status.in_(["ACTIVE", "PENDING"])
    )

    # -----------------------------------------------------------------------
    # 7. Total invoices count
    # -----------------------------------------------------------------------
    total_inv_q = select(func.count(Invoice.id))
    if is_vendor and vendor_obj:
        total_inv_q = total_inv_q.where(Invoice.vendor_id == vendor_obj.id)

    # -----------------------------------------------------------------------
    # 8. Total PO value
    # -----------------------------------------------------------------------
    po_value_q = select(
        func.coalesce(func.sum(PurchaseOrder.total_cents), 0)
    ).where(
        PurchaseOrder.status.notin_(["DRAFT", "CANCELLED"]),
        PurchaseOrder.deleted_at.is_(None),
    )
    if is_vendor and vendor_obj:
        po_value_q = po_value_q.where(PurchaseOrder.vendor_id == vendor_obj.id)
    elif is_manager and department_id:
        po_value_q = (
            po_value_q
            .join(PurchaseRequest, PurchaseOrder.pr_id == PurchaseRequest.id, isouter=True)
            .where(
                or_(
                    PurchaseRequest.department_id == department_id,
                    PurchaseOrder.pr_id == None,  # noqa: E711
                )
            )
        )

    pr_res, po_res, inv_res, open_inv_res, rfq_res, budget_res, inv_status_res, vendor_count_res, total_inv_res, po_value_res = await asyncio.gather(
        db.execute(pr_q),
        db.execute(po_q),
        db.execute(inv_q),
        db.execute(open_inv_q),
        db.execute(rfq_q),
        db.execute(budget_q),
        db.execute(inv_status_q),
        db.execute(vendor_count_q),
        db.execute(total_inv_q),
        db.execute(po_value_q),
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

    # Build invoice status breakdown
    inv_status_rows = inv_status_res.all()
    invoice_status_breakdown = {r.status: int(r.count) for r in inv_status_rows}

    # Group into chart-friendly categories
    approved_count = (
        invoice_status_breakdown.get("APPROVED", 0)
        + invoice_status_breakdown.get("APPROVED_FOR_PAYMENT", 0)
        + invoice_status_breakdown.get("PAID", 0)
        + invoice_status_breakdown.get("MATCHED", 0)
    )
    pending_count = (
        invoice_status_breakdown.get("UPLOADED", 0)
        + invoice_status_breakdown.get("PROCESSING", 0)
    )
    disputed_count = (
        invoice_status_breakdown.get("EXCEPTION", 0)
        + invoice_status_breakdown.get("DISPUTED", 0)
    )

    total_vendors = vendor_count_res.scalar() or 0
    total_invoices = total_inv_res.scalar() or 0
    total_po_value = po_value_res.scalar() or 0

    return {
        "pending_prs": pending_prs,
        "active_pos": active_pos,
        "invoice_exceptions": invoice_exceptions,
        "open_invoices": open_invoices,
        "pending_rfqs": pending_rfqs,
        "budget_utilization": budget_utilization,
        "total_vendors": total_vendors,
        "total_invoices": total_invoices,
        "total_po_value_cents": total_po_value,
        "total_budget_cents": total_budget,
        "total_spent_cents": total_spent,
        "invoice_status_breakdown": invoice_status_breakdown,
        "payment_chart": [
            {"name": "Approved", "value": approved_count, "color": "#22c55e"},
            {"name": "Pending", "value": pending_count, "color": "#f59e0b"},
            {"name": "Disputed", "value": disputed_count, "color": "#ef4444"},
        ],
    }
