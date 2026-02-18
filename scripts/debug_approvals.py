import asyncio
import os
import sys

sys.path.append(os.getcwd())

from api.database import AsyncSessionLocal, set_tenant_context
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from api.models import PurchaseRequest, Approval, User

async def main():
    async with AsyncSessionLocal() as db:
        await set_tenant_context(db, 'a0000000-0000-0000-0000-000000000001')
        
        # Get Pending PRs
        result = await db.execute(select(PurchaseRequest).where(PurchaseRequest.status == "PENDING"))
        prs = result.scalars().all()
        
        print(f"Found {len(prs)} PENDING PRs")
        print("-" * 80)
        for pr in prs:
            print(f"PR: {pr.pr_number} | ID: {pr.id} | Dept: {pr.department_id}")
            
            # Find approvals for this PR
            stmt = select(Approval).where(
                Approval.entity_type == "PurchaseRequest",
                Approval.entity_id == pr.id,
                Approval.status == "PENDING"
            )
            approval_res = await db.execute(stmt)
            active_approval = approval_res.scalars().first()
            
            if active_approval:
                print(f"  Active Step: Level {active_approval.approval_level}")
                if active_approval.approver_id:
                     user_res = await db.execute(select(User).where(User.id == active_approval.approver_id))
                     user = user_res.scalar_one_or_none()
                     print(f"  Approver ID: {active_approval.approver_id}")
                     print(f"  Approver Email: {user.email if user else 'Unknown'}")
                else:
                    print(f"  Approver ID: None")
            else:
                print("  No active PENDING approval step found (Data inconsistency?)")
            print("-" * 80)

if __name__ == "__main__":
    asyncio.run(main())
