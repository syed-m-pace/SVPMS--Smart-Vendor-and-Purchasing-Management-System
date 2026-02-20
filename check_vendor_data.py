import asyncio
from sqlalchemy import select
from api.database import AsyncSessionLocal as SessionLocal, set_tenant_context
from api.models.user import User
from api.models.vendor import Vendor
from api.models.purchase_order import PurchaseOrder

async def check():
    async with SessionLocal() as db:
        user_result = await db.execute(select(User).where(User.email == "syedmuheeb2001@gmail.com"))
        user = user_result.scalar_one_or_none()
        if not user:
            print("User not found: syedmuheeb2001@gmail.com")
            return
        print(f"User: {user.email}, Tenant: {user.tenant_id}")
        
        await set_tenant_context(db, user.tenant_id)
        
        vendor_result = await db.execute(select(Vendor).where(Vendor.email == user.email))
        vendor = vendor_result.scalar_one_or_none()
        if not vendor:
            print("Vendor not found for user.")
            return
        print(f"Vendor: {vendor.id}, {vendor.legal_name}, Status: {vendor.status}, Bank: {vendor.bank_account_number_encrypted}")
        
        po_result = await db.execute(select(PurchaseOrder).where(PurchaseOrder.vendor_id == vendor.id))
        pos = po_result.scalars().all()
        print(f"Found {len(pos)} POs for vendor.")
        for po in pos:
            print(f"PO {po.po_number}, status: {po.status}")

asyncio.run(check())
