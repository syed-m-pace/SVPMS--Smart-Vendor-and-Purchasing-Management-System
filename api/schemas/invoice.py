from typing import List, Optional
from pydantic import BaseModel, Field


class InvoiceLineItemCreate(BaseModel):
    description: str
    quantity: int = Field(..., ge=1)
    unit_price_cents: int = Field(..., ge=1)


class InvoiceCreate(BaseModel):
    po_id: str
    invoice_number: str
    invoice_date: str
    due_date: Optional[str] = None
    total_cents: int = Field(..., ge=1)
    line_items: List[InvoiceLineItemCreate] = Field(default_factory=list)


class InvoiceLineItemResponse(BaseModel):
    id: str
    line_number: int
    description: str
    quantity: int
    unit_price_cents: int

    model_config = {"from_attributes": True}


class InvoiceResponse(BaseModel):
    id: str
    tenant_id: str
    invoice_number: str
    po_id: Optional[str] = None
    vendor_id: str
    status: str
    invoice_date: str
    due_date: Optional[str] = None
    total_cents: int
    currency: str
    document_url: Optional[str] = None
    match_status: Optional[str] = None
    line_items: List[InvoiceLineItemResponse] = []
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class InvoiceDisputeRequest(BaseModel):
    reason: str = Field(..., min_length=10)


class InvoiceOverrideRequest(BaseModel):
    reason: str = Field(..., min_length=10)
