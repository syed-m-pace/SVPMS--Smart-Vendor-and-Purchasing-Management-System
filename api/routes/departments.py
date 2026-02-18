from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.middleware.auth import get_current_user
from api.middleware.tenant import get_db_with_tenant
from api.middleware.authorization import require_roles
from api.models.department import Department
from api.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentResponse
from api.schemas.common import PaginatedResponse, PaginationMeta, build_pagination

logger = structlog.get_logger()
router = APIRouter()


def _to_response(d: Department) -> DepartmentResponse:
    return DepartmentResponse(
        id=str(d.id), tenant_id=str(d.tenant_id), name=d.name,
        code=d.code, manager_id=str(d.manager_id) if d.manager_id else None,
        parent_department_id=str(d.parent_department_id) if d.parent_department_id else None,
        created_at=d.created_at.isoformat() if d.created_at else "",
    )


@router.get("", response_model=PaginatedResponse[DepartmentResponse])
async def list_departments(
    page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    total = (await db.execute(select(func.count(Department.id)))).scalar() or 0
    result = await db.execute(
        select(Department).order_by(Department.name).offset((page - 1) * limit).limit(limit)
    )
    items = [_to_response(d) for d in result.scalars().all()]
    return PaginatedResponse(data=items, pagination=build_pagination(page, limit, total))


@router.get("/{dept_id}", response_model=DepartmentResponse)
async def get_department(
    dept_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(select(Department).where(Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return _to_response(dept)


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    body: DepartmentCreate,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    dept = Department(
        tenant_id=current_user["tenant_id"], name=body.name, code=body.code,
        manager_id=body.manager_id, parent_department_id=body.parent_department_id,
    )
    db.add(dept)
    await db.flush()
    await db.commit()
    await db.refresh(dept)
    return _to_response(dept)


@router.put("/{dept_id}", response_model=DepartmentResponse)
async def update_department(
    dept_id: str, body: DepartmentUpdate,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(select(Department).where(Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(dept, field, val)
    await db.commit()
    await db.refresh(dept)
    return _to_response(dept)


@router.delete("/{dept_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    dept_id: str,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(select(Department).where(Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    await db.delete(dept)
    await db.commit()
