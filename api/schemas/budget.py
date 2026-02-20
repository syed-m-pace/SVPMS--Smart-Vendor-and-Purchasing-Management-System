from typing import Optional
from pydantic import BaseModel, Field
from api.schemas.department import DepartmentResponse


class BudgetCreate(BaseModel):
    department_id: str
    fiscal_year: int
    quarter: int = Field(..., ge=1, le=4)
    total_cents: int = Field(..., gt=0)
    currency: str = "INR"


class BudgetUpdate(BaseModel):
    total_cents: Optional[int] = Field(None, gt=0)


class BudgetResponse(BaseModel):
    id: str
    tenant_id: str
    department_id: str
    fiscal_year: int
    quarter: int
    total_cents: int
    spent_cents: int
    reserved_cents: int = 0
    available_cents: int = 0
    currency: str
    status: str = "ACTIVE"
    created_at: str
    updated_at: str
    department: Optional[DepartmentResponse] = None

    model_config = {"from_attributes": True}
