from typing import Optional
from pydantic import BaseModel, Field


class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    code: Optional[str] = Field(None, max_length=50)
    manager_id: Optional[str] = None
    parent_department_id: Optional[str] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    code: Optional[str] = Field(None, max_length=50)
    manager_id: Optional[str] = None
    parent_department_id: Optional[str] = None


class DepartmentResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    code: Optional[str] = None
    manager_id: Optional[str] = None
    parent_department_id: Optional[str] = None
    created_at: str

    model_config = {"from_attributes": True}
