#!/usr/bin/env python3
"""
Backfill vendor login users for vendor records.

Usage:
  python -m scripts.backfill_vendor_users           # dry-run
  python -m scripts.backfill_vendor_users --apply   # apply changes
  python -m scripts.backfill_vendor_users --apply --tenant-id <uuid>
"""

import argparse
import asyncio
from collections import defaultdict
from typing import Optional

from sqlalchemy import select

from api.database import AsyncSessionLocal
from api.models.user import User
from api.models.vendor import Vendor
from api.services.auth_service import hash_password

DEFAULT_VENDOR_PASSWORD = "SvpmsTest123!"


async def run(apply: bool, tenant_id: Optional[str]):
    summary = defaultdict(int)
    conflicts: list[str] = []

    async with AsyncSessionLocal() as db:
        q = select(Vendor).where(Vendor.deleted_at == None)  # noqa: E711
        if tenant_id:
            q = q.where(Vendor.tenant_id == tenant_id)

        vendors = (await db.execute(q.order_by(Vendor.created_at.asc()))).scalars().all()

        for vendor in vendors:
            summary["vendors_seen"] += 1

            user = (
                await db.execute(select(User).where(User.email == vendor.email))
            ).scalar_one_or_none()

            if not user:
                summary["will_create"] += 1
                if apply:
                    db.add(
                        User(
                            tenant_id=vendor.tenant_id,
                            email=vendor.email,
                            password_hash=hash_password(DEFAULT_VENDOR_PASSWORD),
                            first_name=vendor.legal_name,
                            last_name="Vendor",
                            role="vendor",
                            is_active=True,
                        )
                    )
                    summary["created"] += 1
                continue

            if user.role != "vendor":
                summary["conflicts"] += 1
                conflicts.append(
                    f"{vendor.email}: user role is '{user.role}' (vendor_id={vendor.id})"
                )
                continue

            if str(user.tenant_id) != str(vendor.tenant_id):
                summary["conflicts"] += 1
                conflicts.append(
                    f"{vendor.email}: vendor/user tenant mismatch "
                    f"(vendor_tenant={vendor.tenant_id}, user_tenant={user.tenant_id})"
                )
                continue

            summary["reused"] += 1
            if apply:
                user.is_active = True
                if not user.password_hash:
                    user.password_hash = hash_password(DEFAULT_VENDOR_PASSWORD)
                    summary["password_set"] += 1

        if apply:
            await db.commit()

    print("Backfill summary")
    print(f"  Apply mode: {apply}")
    print(f"  Vendors scanned: {summary['vendors_seen']}")
    print(f"  Users to create: {summary['will_create']}")
    print(f"  Users created: {summary['created']}")
    print(f"  Users reused: {summary['reused']}")
    print(f"  Passwords set: {summary['password_set']}")
    print(f"  Conflicts: {summary['conflicts']}")

    if conflicts:
        print("\nConflicts:")
        for item in conflicts:
            print(f"  - {item}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill vendor users")
    parser.add_argument("--apply", action="store_true", help="Persist changes")
    parser.add_argument("--tenant-id", default=None, help="Optional tenant UUID filter")
    args = parser.parse_args()

    asyncio.run(run(apply=args.apply, tenant_id=args.tenant_id))
