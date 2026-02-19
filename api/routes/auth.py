from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.database import get_db
from api.models.tenant import Tenant
from api.models.user import User
from api.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    RegisterRequest,
    UserResponse,
    ChangePasswordRequest,
)
from api.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
)
from api.config import settings
from api.middleware.auth import get_current_user

logger = structlog.get_logger()

router = APIRouter()


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the authenticated user's password."""
    result = await db.execute(
        select(User).where(User.id == current_user["user_id"], User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password",
        )

    user.password_hash = hash_password(body.new_password)
    await db.commit()

    logger.info("password_changed", user_id=str(user.id))



@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return JWT tokens."""
    result = await db.execute(
        select(User).where(User.email == body.email, User.is_active == True, User.deleted_at == None)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "AUTH_INVALID_CREDENTIALS",
                    "message": "Invalid email or password",
                }
            },
        )

    # Update last_login_at (naive UTC to match TIMESTAMP WITHOUT TIME ZONE column)
    user.last_login_at = datetime.utcnow()
    await db.commit()

    access_token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role,
        email=user.email,
        department_id=str(user.department_id) if user.department_id else None,
    )
    refresh_token = create_refresh_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
    )

    logger.info("user_logged_in", user_id=str(user.id), role=user.role)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Refresh access token using a valid refresh token."""
    try:
        payload = verify_refresh_token(body.refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "AUTH_REFRESH_INVALID",
                    "message": "Invalid or expired refresh token",
                }
            },
        )

    user_id = payload["sub"]
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True, User.deleted_at == None)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "AUTH_USER_NOT_FOUND",
                    "message": "User no longer exists or is deactivated",
                }
            },
        )

    access_token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role,
        email=user.email,
        department_id=str(user.department_id) if user.department_id else None,
    )
    new_refresh_token = create_refresh_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="Bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new tenant with an admin user (first-time setup)."""
    # Check if slug already taken
    existing = await db.execute(
        select(Tenant).where(Tenant.slug == body.tenant_slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "TENANT_SLUG_EXISTS",
                    "message": f"Tenant slug '{body.tenant_slug}' is already taken",
                }
            },
        )

    # Check if email already taken
    existing_user = await db.execute(
        select(User).where(User.email == body.email)
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "USER_EMAIL_EXISTS",
                    "message": f"Email '{body.email}' is already registered",
                }
            },
        )

    # Create tenant
    tenant = Tenant(
        name=body.tenant_name,
        slug=body.tenant_slug,
        status="ACTIVE",
    )
    db.add(tenant)
    await db.flush()  # Get tenant.id

    # Create admin user
    user = User(
        tenant_id=tenant.id,
        email=body.email,
        password_hash=hash_password(body.password),
        first_name=body.first_name,
        last_name=body.last_name,
        role="admin",
        is_active=True,
    )
    db.add(user)
    await db.flush()

    await db.commit()

    access_token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(tenant.id),
        role=user.role,
        email=user.email,
    )
    refresh_token = create_refresh_token(
        user_id=str(user.id),
        tenant_id=str(tenant.id),
    )

    logger.info("tenant_registered", tenant_id=str(tenant.id), admin_email=user.email)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get current authenticated user profile."""
    result = await db.execute(select(User).where(User.id == current_user["user_id"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(
        id=str(user.id),
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        department_id=str(user.department_id) if user.department_id else None,
        is_active=user.is_active,
    )
