from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
import structlog

from api.middleware.auth import get_current_user
from api.middleware.tenant import get_db_with_tenant
from api.middleware.authorization import require_roles
from api.models.budget import Budget
from api.schemas.budget import BudgetCreate, BudgetUpdate, BudgetResponse
from api.schemas.department import DepartmentResponse
from api.schemas.common import PaginatedResponse, build_pagination

logger = structlog.get_logger()
router = APIRouter()


def _to_response(b: Budget) -> BudgetResponse:
    dept = None
    if getattr(b, "department", None):
        d = b.department
        dept = DepartmentResponse(
            id=str(d.id),
            tenant_id=str(d.tenant_id),
            name=d.name,
            code=d.code,
            manager_id=str(d.manager_id) if d.manager_id else None,
            parent_department_id=str(d.parent_department_id) if d.parent_department_id else None,
            created_at=d.created_at.isoformat() if d.created_at else "",
        )

    return BudgetResponse(
        id=str(b.id),
        tenant_id=str(b.tenant_id),
        department_id=str(b.department_id),
        fiscal_year=b.fiscal_year,
        quarter=b.quarter,
        total_cents=b.total_cents,
        spent_cents=b.spent_cents or 0,
        reserved_cents=0,  # computed at query time from budget_reservations
        available_cents=b.total_cents - (b.spent_cents or 0),
        currency=b.currency,
        status=getattr(b, 'status', None) or "ACTIVE",
        created_at=b.created_at.isoformat() if b.created_at else "",
        updated_at=b.updated_at.isoformat() if b.updated_at else "",
        department=dept,
    )


@router.get("", response_model=PaginatedResponse[BudgetResponse])
async def list_budgets(
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=25),
    department_id: str = Query(None),
    fiscal_year: int = Query(None),
    quarter: int = Query(None, ge=1, le=4),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    q = select(Budget).options(joinedload(Budget.department))
    count_q = select(func.count(Budget.id))

    if department_id:
        q = q.where(Budget.department_id == department_id)
        count_q = count_q.where(Budget.department_id == department_id)
    if fiscal_year:
        q = q.where(Budget.fiscal_year == fiscal_year)
        count_q = count_q.where(Budget.fiscal_year == fiscal_year)
    if quarter:
        q = q.where(Budget.quarter == quarter)
        count_q = count_q.where(Budget.quarter == quarter)

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(
        q.order_by(Budget.fiscal_year.desc(), Budget.quarter.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items = [_to_response(b) for b in result.scalars().all()]
    return PaginatedResponse(data=items, pagination=build_pagination(page, limit, total))


@router.get("/{budget_id}", response_model=BudgetResponse)
async def get_budget(
    budget_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(select(Budget).options(joinedload(Budget.department)).where(Budget.id == budget_id))
    budget = result.scalar_one_or_none()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    return _to_response(budget)


@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    body: BudgetCreate,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("finance", "finance_head", "cfo", "admin", "manager")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    # Check for duplicate budget (same dept + year + quarter)
    existing = await db.execute(
        select(Budget).where(
            Budget.department_id == body.department_id,
            Budget.fiscal_year == body.fiscal_year,
            Budget.quarter == body.quarter,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Budget already exists for this department/year/quarter",
        )

    budget = Budget(
        tenant_id=current_user["tenant_id"],
        department_id=body.department_id,
        fiscal_year=body.fiscal_year,
        quarter=body.quarter,
        total_cents=body.total_cents,
        spent_cents=0,
        currency=body.currency,
    )
    db.add(budget)
    await db.flush()

    result = await db.execute(select(Budget).options(joinedload(Budget.department)).where(Budget.id == budget.id))
    budget_with_dept = result.scalar_one()
    return _to_response(budget_with_dept)


@router.patch("/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: str,
    body: BudgetUpdate,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("finance", "finance_head", "cfo", "admin", "manager")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(
        select(Budget)
        .options(joinedload(Budget.department))
        .where(Budget.id == budget_id)
        .with_for_update(of=Budget)
    )
    budget = result.scalar_one_or_none()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    if body.total_cents is not None:
        if body.total_cents < (budget.spent_cents or 0):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot set total below already spent amount",
            )
        budget.total_cents = body.total_cents

    await db.flush()

    result = await db.execute(select(Budget).options(joinedload(Budget.department)).where(Budget.id == budget.id))
    budget_with_dept = result.scalar_one()
    return _to_response(budget_with_dept)
