from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.middleware.auth import get_current_user
from api.middleware.tenant import get_db_with_tenant
from api.middleware.authorization import require_roles
from api.models.user import User
from api.schemas.auth import UserResponse, UserCreateRequest
from api.schemas.common import PaginatedResponse, build_pagination
from api.schemas.common import PaginatedResponse, build_pagination
from api.services.auth_service import hash_password
from api.services.storage import r2_client

logger = structlog.get_logger()
router = APIRouter()


def _to_response(u: User) -> UserResponse:
    profile_photo_url = u.profile_photo_url
    if profile_photo_url and not profile_photo_url.startswith("http"):
        # Assume it's a key, generate signed URL
        try:
            profile_photo_url = r2_client.get_presigned_url(profile_photo_url)
        except Exception:
            pass  # Keep original or None if failed

    return UserResponse(
        id=str(u.id), email=u.email, first_name=u.first_name, last_name=u.last_name,
        role=u.role, department_id=str(u.department_id) if u.department_id else None,
        profile_photo_url=profile_photo_url,
        is_active=u.is_active,
    )


@router.get("", response_model=PaginatedResponse[UserResponse])
async def list_users(
    page: int = Query(1, ge=1), limit: int = Query(50, ge=1, le=100),
    role: str = Query(None), is_active: bool = Query(None),
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("admin", "manager", "finance", "finance_head", "cfo", "procurement", "procurement_lead")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    q = select(User).where(User.deleted_at == None)
    count_q = select(func.count(User.id)).where(User.deleted_at == None)
    if role:
        q = q.where(User.role == role)
        count_q = count_q.where(User.role == role)
    if is_active is not None:
        q = q.where(User.is_active == is_active)
        count_q = count_q.where(User.is_active == is_active)
    # Manager: only department users
    if current_user["role"] == "manager" and current_user.get("department_id"):
        q = q.where(User.department_id == current_user["department_id"])
        count_q = count_q.where(User.department_id == current_user["department_id"])

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(q.order_by(User.email).offset((page - 1) * limit).limit(limit))
    items = [_to_response(u) for u in result.scalars().all()]
    return PaginatedResponse(data=items, pagination=build_pagination(page, limit, total))


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(select(User).where(User.id == user_id, User.deleted_at == None))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _to_response(user)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreateRequest,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        tenant_id=current_user["tenant_id"], email=body.email,
        password_hash=hash_password(body.password),
        first_name=body.first_name, last_name=body.last_name,
        role=body.role, department_id=body.department_id,
    )
    db.add(user)
    await db.flush()
    await db.commit()
    await db.refresh(user)
    return _to_response(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str, body: dict,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(select(User).where(User.id == user_id, User.deleted_at == None))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    allowed = {"first_name", "last_name", "role", "department_id", "is_active", "profile_photo_url"}
    for k, v in body.items():
        if k in allowed:
            setattr(user, k, v)
    await db.commit()
    await db.refresh(user)
    return _to_response(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    from datetime import datetime
    result = await db.execute(select(User).where(User.id == user_id, User.deleted_at == None))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.deleted_at = datetime.utcnow()
    user.is_active = False
    await db.commit()
