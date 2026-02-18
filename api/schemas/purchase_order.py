from typing import List, Optional
from pydantic import BaseModel, Field


class PoLineItemResponse(BaseModel):
    id: str
    line_number: int
    description: str
    quantity: int
    unit_price_cents: int
    received_quantity: int = 0

    model_config = {"from_attributes": True}


class PurchaseOrderCreate(BaseModel):
    pr_id: str
    vendor_id: str
    expected_delivery_date: Optional[str] = None
    terms_and_conditions: Optional[str] = None


class PurchaseOrderResponse(BaseModel):
    id: str
    tenant_id: str
    po_number: str
    pr_id: Optional[str] = None
    vendor_id: str
    status: str
    total_cents: int
    currency: str
    expected_delivery_date: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    line_items: List[PoLineItemResponse] = []
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class CancelRequest(BaseModel):
    reason: str = Field(..., min_length=1)
