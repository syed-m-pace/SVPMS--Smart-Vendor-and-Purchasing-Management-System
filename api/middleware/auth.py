from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
import structlog

from api.services.auth_service import verify_access_token

logger = structlog.get_logger()

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """FastAPI dependency: extract and verify JWT, return user claims dict."""
    token = credentials.credentials
    try:
        payload = verify_access_token(token)
        return {
            "user_id": payload["sub"],
            "tenant_id": payload["tenant_id"],
            "role": payload["role"],
            "email": payload["email"],
            "department_id": payload.get("department_id"),
        }
    except JWTError as e:
        logger.warning("auth_token_invalid", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "AUTH_TOKEN_INVALID",
                    "message": "Invalid or expired token",
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
