from typing import Optional
from pydantic import BaseModel, Field


class ApprovalResponse(BaseModel):
    id: str
    tenant_id: str
    entity_type: str
    entity_id: str
    approver_id: str
    approval_level: int
    status: str
    comments: Optional[str] = None
    approved_at: Optional[str] = None
    created_at: str

    model_config = {"from_attributes": True}


class ApprovalActionRequest(BaseModel):
    comment: Optional[str] = Field(None, max_length=500)
