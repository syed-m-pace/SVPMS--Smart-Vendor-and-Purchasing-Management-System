from typing import Optional
from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: str
    tenant_id: str
    actor_id: Optional[str] = None
    actor_email: Optional[str] = None
    action: str
    entity_type: str
    entity_id: str
    before_state: Optional[dict] = None
    after_state: Optional[dict] = None
    created_at: str

    model_config = {"from_attributes": True}
