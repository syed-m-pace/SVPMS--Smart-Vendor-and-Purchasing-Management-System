import asyncio
import os
import sys
from sqlalchemy import select, func, text

sys.path.append(os.getcwd())

from api.database import AsyncSessionLocal, set_tenant_context
from api.models import PurchaseRequest, Approval, Department, User, Budget

async def main():
    async with AsyncSessionLocal() as db:
        await set_tenant_context(db, 'a0000000-0000-0000-0000-000000000001')
        print("Starting Database Integrity Check...")
        print("=" * 60)

        # 1. Check for Duplicate Departments
        print("\n[1] Checking for Duplicate Departments...")
        stmt = select(Department.name, func.count(Department.id)).group_by(Department.name).having(func.count(Department.id) > 1)
        duplicates = await db.execute(stmt)
        dupes = duplicates.all()
        if dupes:
            print(f"❌ Found duplicate departments: {dupes}")
        else:
            print("✅ No duplicate departments found.")

        # 2. Check for Departments without Managers
        print("\n[2] Checking for Departments without Managers...")
        stmt = select(Department).where(Department.manager_id == None)
        res = await db.execute(stmt)
        no_manager = res.scalars().all()
        if no_manager:
            print(f"⚠️  Found {len(no_manager)} departments without managers:")
            for d in no_manager:
                print(f"   - {d.name} (ID: {d.id})")
        else:
            print("✅ All departments have assigned managers.")

        # 3. Check for Pending PRs without Active Approvals
        print("\n[3] Checking for PENDING PRs with properly linked Approvals...")
        stmt = select(PurchaseRequest).where(PurchaseRequest.status == 'PENDING')
        res = await db.execute(stmt)
        pending_prs = res.scalars().all()
        
        orphaned_prs = []
        for pr in pending_prs:
            stmt_app = select(Approval).where(
                Approval.entity_type == "PurchaseRequest",
                Approval.entity_id == pr.id,
                Approval.status == "PENDING"
            )
            app_res = await db.execute(stmt_app)
            if not app_res.scalar_one_or_none():
                orphaned_prs.append(pr)
        
        if orphaned_prs:
            print(f"❌ Found {len(orphaned_prs)} PENDING PRs with NO active approval record:")
            for pr in orphaned_prs:
                print(f"   - PR: {pr.pr_number} (ID: {pr.id})")
        else:
            print("✅ All PENDING PRs have active approval records.")

        # 4. Check for Orphaned Approvals (pointing to non-existent entities)
        # This is harder to check generally without dynamic queries, but we can check specific types
        print("\n[4] Checking for Orphaned Approvals...")
        stmt = select(Approval).where(Approval.entity_type == "PurchaseRequest")
        res = await db.execute(stmt)
        approvals = res.scalars().all()
        orphaned_approvals = []
        for app in approvals:
            stmt_pr = select(PurchaseRequest).where(PurchaseRequest.id == app.entity_id)
            pr_res = await db.execute(stmt_pr)
            if not pr_res.scalar_one_or_none():
                 orphaned_approvals.append(app)
        
        if orphaned_approvals:
            print(f"❌ Found {len(orphaned_approvals)} Approvals pointing to missing PRs.")
        else:
            print("✅ All PR Approvals link to valid PRs.")

        print("\n" + "=" * 60)
        print("Integrity Check Complete.")

if __name__ == "__main__":
    asyncio.run(main())
