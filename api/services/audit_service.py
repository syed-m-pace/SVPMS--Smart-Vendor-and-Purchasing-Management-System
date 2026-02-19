"""Audit logging service — records entity state changes."""

from typing import Optional
from datetime import datetime
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from api.models.audit_log import AuditLog

logger = structlog.get_logger()


def _to_uuid(value: Optional[str], field_name: str, required: bool = False) -> Optional[uuid.UUID]:
    if value is None:
        if required:
            raise ValueError(f"{field_name} is required")
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        if required:
            raise ValueError(f"{field_name} must be a valid UUID")
        logger.warning("audit_invalid_uuid", field=field_name, value=str(value))
        return None


def _compute_changed_fields(
    before: Optional[dict], after: Optional[dict]
) -> Optional[list[str]]:
    """Diff two state dicts and return list of changed field names."""
    if not before or not after:
        return None
    changed = []
    all_keys = set(before.keys()) | set(after.keys())
    for key in sorted(all_keys):
        if before.get(key) != after.get(key):
            changed.append(key)
    return changed or None


async def create_audit_log(
    session: AsyncSession,
    tenant_id: str,
    actor_id: Optional[str],
    action: str,
    entity_type: str,
    entity_id: str,
    before_state: Optional[dict] = None,
    after_state: Optional[dict] = None,
    actor_email: Optional[str] = None,
) -> AuditLog:
    """
    Create an audit log entry.

    Uses session.flush() — caller owns the transaction.
    """
    changed_fields = _compute_changed_fields(before_state, after_state)

    audit = AuditLog(
        tenant_id=_to_uuid(tenant_id, "tenant_id", required=True),
        actor_id=_to_uuid(actor_id, "actor_id"),
        actor_email=actor_email,
        action=action,
        entity_type=entity_type,
        entity_id=_to_uuid(entity_id, "entity_id", required=True),
        before_state=before_state,
        after_state=after_state,
        changed_fields=changed_fields,
        created_at=datetime.utcnow(),
    )
    session.add(audit)
    await session.flush()

    logger.info(
        "audit_log_created",
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
    )
    return audit
