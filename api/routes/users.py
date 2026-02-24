from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.middleware.auth import get_current_user
from api.middleware.tenant import get_db_with_tenant
from api.middleware.authorization import require_roles
from api.models.user import User
from api.schemas.auth import UserCreateRequest, UserResponse, UserUpdateRequest
from api.schemas.common import PaginatedResponse, build_pagination
from api.services.auth_service import hash_password
from api.services.storage import r2_client

logger = structlog.get_logger()
router = APIRouter()


def _to_response(u: User) -> UserResponse:
    profile_photo_url = getattr(u, "profile_photo_url", None)
    if profile_photo_url and not profile_photo_url.startswith("http"):
        try:
            profile_photo_url = r2_client.get_presigned_url(profile_photo_url)
        except Exception:
            pass

    return UserResponse(
        id=str(u.id),
        email=u.email,
        first_name=u.first_name,
        last_name=u.last_name,
        role=u.role,
        department_id=str(u.department_id) if u.department_id else None,
        profile_photo_url=profile_photo_url,
        is_active=u.is_active,
    )


@router.get("", response_model=PaginatedResponse[UserResponse])
async def list_users(
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(20, ge=1, le=25),
    role: str = Query(None),
    is_active: bool = Query(None),
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(
        require_roles(
            "admin",
            "manager",
            "finance",
            "finance_head",
            "cfo",
            "procurement",
            "procurement_lead",
        )
    ),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    q = select(User).where(User.deleted_at == None)  # noqa: E711
    count_q = select(func.count(User.id)).where(User.deleted_at == None)  # noqa: E711
    if role:
        q = q.where(User.role == role)
        count_q = count_q.where(User.role == role)
    if is_active is not None:
        q = q.where(User.is_active == is_active)
        count_q = count_q.where(User.is_active == is_active)

    if current_user["role"] == "manager" and current_user.get("department_id"):
        q = q.where(User.department_id == current_user["department_id"])
        count_q = count_q.where(User.department_id == current_user["department_id"])

    total = (await db.execute(count_q)).scalar() or 0
    result = await db.execute(q.order_by(User.email).offset((page - 1) * limit).limit(limit))
    items = [_to_response(u) for u in result.scalars().all()]
    return PaginatedResponse(data=items, pagination=build_pagination(page, limit, total))


@router.get("/me", response_model=UserResponse)
async def get_me_alias(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(
        select(User).where(User.id == current_user["user_id"], User.deleted_at == None)  # noqa: E711
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _to_response(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(select(User).where(User.id == user_id, User.deleted_at == None))  # noqa: E711
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
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        tenant_id=current_user["tenant_id"],
        email=body.email,
        password_hash=hash_password(body.password),
        first_name=body.first_name,
        last_name=body.last_name,
        role=body.role,
        department_id=body.department_id,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return _to_response(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    body: UserUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    if current_user["role"] != "admin" and current_user["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this user")

    result = await db.execute(select(User).where(User.id == user_id, User.deleted_at == None))  # noqa: E711
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Non-admin users can only update their own profile fields
    update_data = body.model_dump(exclude_none=True)
    admin_only_fields = {"role", "department_id", "is_active"}

    for field, value in update_data.items():
        if field in admin_only_fields and current_user["role"] != "admin":
            continue
        setattr(user, field, value)

    await db.flush()
    await db.refresh(user)
    return _to_response(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    _auth: None = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    result = await db.execute(select(User).where(User.id == user_id, User.deleted_at == None))  # noqa: E711
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.deleted_at = datetime.utcnow()
    user.is_active = False
