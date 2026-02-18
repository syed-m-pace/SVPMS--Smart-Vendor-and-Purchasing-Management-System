from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid

from jose import jwt, JWTError
from passlib.context import CryptContext
import structlog

from api.config import settings

logger = structlog.get_logger()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------- password helpers ----------

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ---------- JWT key loading ----------

_private_key: Optional[str] = None
_public_key: Optional[str] = None


def _load_private_key() -> str:
    global _private_key
    if _private_key is None:
        with open(settings.JWT_PRIVATE_KEY_PATH, "r") as f:
            _private_key = f.read()
    return _private_key


def _load_public_key() -> str:
    global _public_key
    if _public_key is None:
        with open(settings.JWT_PUBLIC_KEY_PATH, "r") as f:
            _public_key = f.read()
    return _public_key


# ---------- token generation ----------

def create_access_token(
    user_id: str,
    tenant_id: str,
    role: str,
    email: str,
    department_id: Optional[str] = None,
) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role,
        "email": email,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
    }
    if department_id:
        claims["department_id"] = str(department_id)
    return jwt.encode(claims, _load_private_key(), algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str, tenant_id: str) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "iat": now,
        "exp": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "type": "refresh",
    }
    return jwt.encode(claims, _load_private_key(), algorithm=settings.JWT_ALGORITHM)


# ---------- token verification ----------

def decode_token(token: str) -> dict:
    """Decode and verify a JWT token. Raises JWTError on failure."""
    return jwt.decode(token, _load_public_key(), algorithms=[settings.JWT_ALGORITHM])


def verify_access_token(token: str) -> dict:
    """Verify an access token and return its claims."""
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise JWTError("Not an access token")
    return payload


def verify_refresh_token(token: str) -> dict:
    """Verify a refresh token and return its claims."""
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise JWTError("Not a refresh token")
    return payload
