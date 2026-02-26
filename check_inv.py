import asyncio
import os
import sys

from api.database import AsyncSessionLocal
from api.models.vendor import Vendor
from api.models.invoice import Invoice
from sqlalchemy import select

async def check():
    try:
        async with AsyncSessionLocal() as db:
            vendor = (await db.execute(select(Vendor).where(Vendor.email == "syedmuheeb2001+1@gmail.com"))).scalar_one_or_none()
            if not vendor:
                print("Vendor not found")
                return
            invoices = (await db.execute(select(Invoice).where(Invoice.vendor_id == vendor.id))).scalars().all()
            if not invoices:
                print("No invoices found for this vendor.")
            for i in invoices:
                print(f"Invoice {i.invoice_number}: status={i.status}, match_status={i.match_status}, exceptions={i.match_exceptions}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check())
