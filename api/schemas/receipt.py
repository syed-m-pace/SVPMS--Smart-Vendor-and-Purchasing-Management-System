from typing import List, Optional
from pydantic import BaseModel, Field


class ReceiptLineItemCreate(BaseModel):
    po_line_item_id: str
    quantity_received: int = Field(..., ge=1)
    condition: str = "GOOD"
    notes: Optional[str] = None


class ReceiptCreate(BaseModel):
    po_id: str
    notes: Optional[str] = None
    document_key: Optional[str] = None
    line_items: List[ReceiptLineItemCreate] = Field(..., min_length=1)


class ReceiptLineItemResponse(BaseModel):
    id: str
    po_line_item_id: str
    quantity_received: int
    condition: str
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class ReceiptResponse(BaseModel):
    id: str
    tenant_id: str
    receipt_number: str
    po_id: str
    received_by: str
    receipt_date: str
    status: str
    notes: Optional[str] = None
    document_key: Optional[str] = None
    line_items: List[ReceiptLineItemResponse] = []
    created_at: str

    model_config = {"from_attributes": True}
