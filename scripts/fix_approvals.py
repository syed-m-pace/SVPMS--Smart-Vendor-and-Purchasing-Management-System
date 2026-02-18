import asyncio
import os
import sys

sys.path.append(os.getcwd())

from api.database import AsyncSessionLocal, set_tenant_context
from sqlalchemy import select
from api.models import PurchaseRequest, Approval, Department

async def main():
    async with AsyncSessionLocal() as db:
        await set_tenant_context(db, 'a0000000-0000-0000-0000-000000000001')
        
        # Get PENDING PRs
        result = await db.execute(select(PurchaseRequest).where(PurchaseRequest.status == "PENDING"))
        prs = result.scalars().all()
        
        for pr in prs:
            # Check for existing pending approval
            stmt = select(Approval).where(
                Approval.entity_type == "PurchaseRequest",
                Approval.entity_id == pr.id,
                Approval.status == "PENDING"
            )
            existing = await db.execute(stmt)
            if existing.scalar_one_or_none():
                print(f"PR {pr.pr_number}: Has pending approval. Skipping.")
                continue

            print(f"PR {pr.pr_number}: Missing approval. Fixing...")
            
            # Get Department Manager
            dept_res = await db.execute(select(Department).where(Department.id == pr.department_id))
            dept = dept_res.scalar_one()
            
            if not dept.manager_id:
                print(f"  Error: Department {dept.name} has no manager. Cannot assign approval.")
                continue

            # Create Approval
            new_approval = Approval(
                tenant_id=pr.tenant_id,
                entity_type="PurchaseRequest",
                entity_id=pr.id,
                approver_id=dept.manager_id,
                approval_level=1,
                status="PENDING"
            )
            db.add(new_approval)
            print(f"  Created approval for Manager ID: {dept.manager_id}")

        await db.commit()
        print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
