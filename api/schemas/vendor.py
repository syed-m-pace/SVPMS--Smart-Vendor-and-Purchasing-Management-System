from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class VendorCreate(BaseModel):
    legal_name: str = Field(..., min_length=2, max_length=200)
    tax_id: str = Field(..., pattern=r"^[A-Z0-9]{10,15}$")
    email: EmailStr
    phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    bank_account_number: Optional[str] = Field(None, min_length=8, max_length=34)
    bank_name: Optional[str] = Field(None, max_length=200)
    ifsc_code: Optional[str] = Field(None, pattern=r"^[A-Z]{4}0[A-Z0-9]{6}$")


class VendorUpdate(BaseModel):
    legal_name: Optional[str] = Field(None, min_length=2, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    bank_name: Optional[str] = None
    ifsc_code: Optional[str] = None


class VendorResponse(BaseModel):
    id: str
    tenant_id: str
    legal_name: str
    tax_id: Optional[str] = None
    email: str
    phone: Optional[str] = None
    status: str
    risk_score: Optional[int] = None
    rating: Optional[float] = None
    bank_name: Optional[str] = None
    ifsc_code: Optional[str] = None
    bank_account: Optional[str] = None
    contact_person: Optional[str] = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class VendorBlockRequest(BaseModel):
    reason: str = Field(..., min_length=10)
