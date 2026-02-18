import asyncio
import os
import sys

sys.path.append(os.getcwd())

from api.database import AsyncSessionLocal, set_tenant_context
from sqlalchemy import delete, select
from api.models import Department

async def main():
    async with AsyncSessionLocal() as db:
        await set_tenant_context(db, 'a0000000-0000-0000-0000-000000000001')
        
        # Find IDs
        result = await db.execute(select(Department.id).where(Department.name == "Concur Dept"))
        dept_ids = result.scalars().all()
        
        if not dept_ids:
            print("No Concur Depts found")
            return

        from api.models import Budget, PurchaseRequest, User
        
        # Delete PRs first (they reference departments)
        stmt_prs = delete(PurchaseRequest).where(PurchaseRequest.department_id.in_(dept_ids))
        res_prs = await db.execute(stmt_prs)
        print(f"Deleted {res_prs.rowcount} purchase requests")

        # Delete Users (if any reference these departments)
        stmt_users = delete(User).where(User.department_id.in_(dept_ids))
        res_users = await db.execute(stmt_users)
        print(f"Deleted {res_users.rowcount} users")

        # Delete Budgets
        stmt_budgets = delete(Budget).where(Budget.department_id.in_(dept_ids))
        res_budgets = await db.execute(stmt_budgets)
        print(f"Deleted {res_budgets.rowcount} budgets")

        # Delete Departments
        stmt = delete(Department).where(Department.id.in_(dept_ids))
        result = await db.execute(stmt)
        await db.commit()
        
        print(f"Deleted {result.rowcount} departments")

if __name__ == "__main__":
    asyncio.run(main())
