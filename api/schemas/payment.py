from typing import Optional
from pydantic import BaseModel


class PaymentResponse(BaseModel):
    id: str
    tenant_id: str
    invoice_id: str
    amount_cents: int
    currency: str
    status: str
    paid_at: Optional[str] = None
    created_at: str

    model_config = {"from_attributes": True}
