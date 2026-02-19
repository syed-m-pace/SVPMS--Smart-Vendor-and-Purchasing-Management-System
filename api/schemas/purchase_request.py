from typing import List, Optional
from pydantic import BaseModel, Field


class PrLineItemCreate(BaseModel):
    description: str = Field(..., min_length=3, max_length=500)
    quantity: int = Field(..., ge=1, le=999999)
    unit_price_cents: int = Field(..., ge=1)
    category: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=1000)


class PurchaseRequestCreate(BaseModel):
    department_id: str
    description: Optional[str] = Field(None, max_length=1000)
    justification: Optional[str] = None
    line_items: List[PrLineItemCreate] = Field(..., min_length=1, max_length=100)


class PurchaseRequestUpdate(BaseModel):
    description: Optional[str] = Field(None, max_length=1000)
    justification: Optional[str] = None
    line_items: Optional[List[PrLineItemCreate]] = None


class PrLineItemResponse(BaseModel):
    id: str
    line_number: int
    description: str
    quantity: int
    unit_price_cents: int
    category: Optional[str] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class PurchaseRequestResponse(BaseModel):
    id: str
    tenant_id: str
    pr_number: str
    requester_id: str
    department_id: str
    status: str
    total_cents: int
    currency: str
    description: Optional[str] = None
    justification: Optional[str] = None
    line_items: List[PrLineItemResponse] = []
    created_at: str
    updated_at: str
    submitted_at: Optional[str] = None
    approved_at: Optional[str] = None

    model_config = {"from_attributes": True}


class ApproveRejectRequest(BaseModel):
    comment: Optional[str] = Field(None, max_length=500)


class RejectRequest(BaseModel):
    reason: str = Field(..., min_length=10, max_length=1000)


class RetractRequest(BaseModel):
    reason: Optional[str] = Field(None, min_length=3, max_length=1000)
