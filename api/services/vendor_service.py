# api/services/vendor_service.py
"""
Shared vendor lookup utilities used by multiple route modules.
"""

from typing import Optional

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.vendor import Vendor


async def resolve_vendor_for_user(
    db: AsyncSession, current_user: dict
) -> Optional[Vendor]:
    """
    Look up the Vendor record for the authenticated vendor user.

    Vendors authenticate as users with the 'vendor' role; their user email
    matches their vendor record's email. Prefers ACTIVE status over others
    if multiple records exist.
    """
    result = await db.execute(
        select(Vendor)
        .where(
            Vendor.tenant_id == current_user["tenant_id"],
            Vendor.email == current_user["email"],
            Vendor.deleted_at == None,  # noqa: E711
        )
        .order_by(
            case((Vendor.status == "ACTIVE", 0), else_=1),
            Vendor.created_at.asc(),
        )
    )
    return result.scalars().first()
