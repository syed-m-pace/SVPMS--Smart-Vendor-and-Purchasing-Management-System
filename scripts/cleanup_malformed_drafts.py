#!/usr/bin/env python3
"""
Identify and optionally soft-delete malformed draft PRs/vendors.

Usage:
  python -m scripts.cleanup_malformed_drafts           # dry-run
  python -m scripts.cleanup_malformed_drafts --apply   # soft-delete malformed drafts
  python -m scripts.cleanup_malformed_drafts --tenant-id <uuid>
"""

import argparse
import asyncio
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select

from api.database import AsyncSessionLocal
from api.models.purchase_request import PurchaseRequest, PrLineItem
from api.models.user import User
from api.models.vendor import Vendor

KNOWN_PR_NUMBERS = {"PR-000009", "PR-000010", "PR-000011"}


async def _is_pr_malformed(db, pr: PurchaseRequest) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    line_count = (
        await db.execute(select(func.count(PrLineItem.id)).where(PrLineItem.pr_id == pr.id))
    ).scalar() or 0
    if line_count == 0:
        reasons.append("no_line_items")

    if (pr.total_cents or 0) <= 0:
        reasons.append("non_positive_total")

    requester_exists = (
        await db.execute(select(User.id).where(User.id == pr.requester_id, User.deleted_at == None))  # noqa: E711
    ).scalar_one_or_none()
    if not requester_exists:
        reasons.append("missing_requester")

    return (len(reasons) > 0, reasons)


async def run(apply: bool, tenant_id: Optional[str]):
    async with AsyncSessionLocal() as db:
        pr_query = select(PurchaseRequest).where(
            PurchaseRequest.status == "DRAFT",
            PurchaseRequest.deleted_at == None,  # noqa: E711
        )
        vendor_query = select(Vendor).where(
            Vendor.status == "DRAFT",
            Vendor.deleted_at == None,  # noqa: E711
        )

        if tenant_id:
            pr_query = pr_query.where(PurchaseRequest.tenant_id == tenant_id)
            vendor_query = vendor_query.where(Vendor.tenant_id == tenant_id)

        draft_prs = (await db.execute(pr_query.order_by(PurchaseRequest.created_at.asc()))).scalars().all()
        draft_vendors = (await db.execute(vendor_query.order_by(Vendor.created_at.asc()))).scalars().all()

        malformed_prs: list[tuple[PurchaseRequest, list[str]]] = []
        known_pr_checks: list[str] = []
        for pr in draft_prs:
            malformed, reasons = await _is_pr_malformed(db, pr)
            if malformed:
                malformed_prs.append((pr, reasons))
            if pr.pr_number in KNOWN_PR_NUMBERS:
                label = "MALFORMED" if malformed else "VALID"
                known_pr_checks.append(f"{pr.pr_number} ({pr.id}) => {label}; reasons={reasons}")

        malformed_vendors: list[tuple[Vendor, list[str]]] = []
        for vendor in draft_vendors:
            reasons: list[str] = []
            if not vendor.legal_name or not vendor.legal_name.strip():
                reasons.append("missing_legal_name")
            if not vendor.email or not vendor.email.strip():
                reasons.append("missing_email")
            if not vendor.tax_id or not str(vendor.tax_id).strip():
                reasons.append("missing_tax_id")
            if reasons:
                malformed_vendors.append((vendor, reasons))

        print("Draft integrity report")
        print(f"  Apply mode: {apply}")
        print(f"  Draft PRs scanned: {len(draft_prs)}")
        print(f"  Malformed draft PRs: {len(malformed_prs)}")
        print(f"  Draft vendors scanned: {len(draft_vendors)}")
        print(f"  Malformed draft vendors: {len(malformed_vendors)}")

        print("\nKnown PR checks")
        if known_pr_checks:
            for row in known_pr_checks:
                print(f"  - {row}")
        else:
            print("  - None of PR-000009/10/11 found in current draft set")

        if malformed_prs:
            print("\nMalformed draft PRs")
            for pr, reasons in malformed_prs:
                print(f"  - {pr.pr_number} ({pr.id}) reasons={reasons}")

        if malformed_vendors:
            print("\nMalformed draft vendors")
            for vendor, reasons in malformed_vendors:
                print(f"  - {vendor.legal_name} ({vendor.id}) reasons={reasons}")

        if apply:
            now = datetime.utcnow()
            for pr, _ in malformed_prs:
                pr.deleted_at = now
            for vendor, _ in malformed_vendors:
                vendor.deleted_at = now

            await db.commit()
            print("\nApplied soft deletes to malformed drafts.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cleanup malformed draft PRs/vendors")
    parser.add_argument("--apply", action="store_true", help="Persist soft-delete changes")
    parser.add_argument("--tenant-id", default=None, help="Optional tenant UUID filter")
    args = parser.parse_args()

    asyncio.run(run(apply=args.apply, tenant_id=args.tenant_id))
