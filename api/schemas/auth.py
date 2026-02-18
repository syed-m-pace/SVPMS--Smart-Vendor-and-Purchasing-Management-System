import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

PASSWORD_REGEX = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
)

VALID_ROLES = (
    "admin",
    "manager",
    "finance",
    "finance_head",
    "cfo",
    "procurement",
    "procurement_lead",
    "vendor",
)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)
    mfa_code: Optional[str] = Field(None, pattern=r"^\d{6}$")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RegisterRequest(BaseModel):
    """First-time tenant + admin user registration."""
    tenant_name: str = Field(..., min_length=1, max_length=200)
    tenant_slug: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z0-9-]+$")
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not PASSWORD_REGEX.match(v):
            raise ValueError(
                "Password must contain: uppercase, lowercase, number, and special character (@$!%*?&)"
            )
        return v


class UserResponse(BaseModel):
    id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str
    department_id: Optional[str] = None
    is_active: bool

    model_config = {"from_attributes": True}


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: str
    department_id: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not PASSWORD_REGEX.match(v):
            raise ValueError(
                "Password must contain: uppercase, lowercase, number, and special character (@$!%*?&)"
            )
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in VALID_ROLES:
            raise ValueError(f"Invalid role. Must be one of: {VALID_ROLES}")
        return v
