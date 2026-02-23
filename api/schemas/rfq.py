from typing import List, Optional
from pydantic import BaseModel, Field


class RfqLineItemCreate(BaseModel):
    description: str
    quantity: int = Field(..., ge=1)
    specifications: Optional[str] = None


class RfqCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    pr_id: Optional[str] = None
    deadline: str
    line_items: List[RfqLineItemCreate] = Field(..., min_length=1)


class RfqBidCreate(BaseModel):
    total_cents: int = Field(..., ge=1)
    delivery_days: Optional[int] = None
    notes: Optional[str] = None


class RfqAwardRequest(BaseModel):
    bid_id: str


class RfqLineItemResponse(BaseModel):
    id: str
    description: str
    quantity: int
    specifications: Optional[str] = None

    model_config = {"from_attributes": True}


class RfqBidResponse(BaseModel):
    id: str
    rfq_id: str
    vendor_id: str
    total_cents: int
    delivery_days: Optional[int] = None
    notes: Optional[str] = None
    score: Optional[float] = None
    submitted_at: str

    model_config = {"from_attributes": True}


class RfqResponse(BaseModel):
    id: str
    tenant_id: str
    rfq_number: str
    title: str
    pr_id: Optional[str] = None
    status: str
    deadline: str
    created_by: str
    awarded_vendor_id: Optional[str] = None
    awarded_po_id: Optional[str] = None
    line_items: List[RfqLineItemResponse] = []
    bids: List[RfqBidResponse] = []
    created_at: str

    model_config = {"from_attributes": True}
