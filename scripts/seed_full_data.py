"""
Comprehensive data seeding script for SVPMS.
Performs the following operations in order:
  1. Delete most contracts, keep 5 random
  2. Delete most vendors, keep 5 most recent
  3. Generate 150 random PRs (with line items)
  4. Approve 124 of those PRs
  5. Create 124 POs from approved PRs
  6. Assign 100 POs to random active vendors
  7. Acknowledge 85 POs from vendor side
  8. Upload invoices for 60 of the acknowledged POs
  9. Approve 45 invoices, raise exception on 10

Run:
  source .venv/bin/activate && PYTHONPATH=. python scripts/seed_full_data.py
"""
import asyncio
import random
import ssl
import uuid
from datetime import datetime, timedelta, date

import asyncpg
from api.config import settings


# ── Connection ───────────────────────────────────────────────────
def _get_dsn() -> str:
    url = settings.DATABASE_URL
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    url = url.replace("?sslmode=require", "").replace("&sslmode=require", "")
    return url


# ── Helpers ──────────────────────────────────────────────────────
PR_DESCRIPTIONS = [
    "Office supplies for Q1",
    "Server hardware refresh",
    "Cloud hosting annual renewal",
    "Marketing campaign materials",
    "Employee training program",
    "Software licenses renewal",
    "Data center maintenance",
    "Network infrastructure upgrade",
    "Security audit tooling",
    "HR onboarding kits",
    "Furniture for new wing",
    "Travel equipment procurement",
    "Lab equipment for R&D",
    "Conference room AV setup",
    "Warehouse packing supplies",
]

LINE_ITEM_DESCS = [
    "Laptop Dell XPS 15", "Monitor 27-inch 4K", "Mechanical Keyboard",
    "Wireless Mouse", "USB-C Hub", "Standing Desk", "Office Chair",
    "Whiteboard 6ft", "Webcam HD", "Headset Noise-Cancelling",
    "Server Rack Unit", "SSD 1TB NVMe", "RAM 32GB DDR5", "Ethernet Cable Cat6",
    "UPS 1500VA", "Printer Laser", "Scanner Flatbed", "External HDD 4TB",
    "Projector 4K", "Conference Phone",
]


async def main():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    conn = await asyncpg.connect(_get_dsn(), ssl=ctx)

    # ── Resolve tenant + user ────────────────────────────────────
    tenant_id = await conn.fetchval("SELECT id FROM tenants LIMIT 1")
    print(f"Tenant: {tenant_id}")

    await conn.execute(
        "SELECT set_config('app.current_tenant_id', $1, false)",
        str(tenant_id),
    )

    # Admin user for approvals
    admin_user = await conn.fetchval(
        "SELECT id FROM users WHERE tenant_id = $1 AND role = 'admin' LIMIT 1",
        tenant_id,
    )
    print(f"Admin user: {admin_user}")

    # Departments
    dept_rows = await conn.fetch(
        "SELECT id FROM departments WHERE tenant_id = $1", tenant_id
    )
    dept_ids = [r["id"] for r in dept_rows]
    print(f"Departments: {len(dept_ids)}")

    # Non-vendor users for PR requesters
    user_rows = await conn.fetch(
        "SELECT id FROM users WHERE tenant_id = $1 AND role != 'vendor'",
        tenant_id,
    )
    user_ids = [r["id"] for r in user_rows]

    # ═════════════════════════════════════════════════════════════
    # STEP 1: Delete most contracts, keep 5 random
    # ═════════════════════════════════════════════════════════════
    print("\n══ Step 1: Cleanup contracts (keep 5 random) ══")
    keep_ids = await conn.fetch(
        "SELECT id FROM contracts WHERE tenant_id = $1 ORDER BY random() LIMIT 5",
        tenant_id,
    )
    keep_contract_ids = [r["id"] for r in keep_ids]
    # Delete associated contract_vendors first
    del_cv = await conn.execute(
        "DELETE FROM contract_vendors WHERE tenant_id = $1 AND contract_id NOT IN (SELECT unnest($2::uuid[]))",
        tenant_id, keep_contract_ids,
    )
    del_c = await conn.execute(
        "DELETE FROM contracts WHERE tenant_id = $1 AND id NOT IN (SELECT unnest($2::uuid[]))",
        tenant_id, keep_contract_ids,
    )
    print(f"  Kept {len(keep_contract_ids)} contracts; deleted rest. {del_c}")

    # ═════════════════════════════════════════════════════════════
    # STEP 2: Delete most vendors, keep 5 most recent
    # ═════════════════════════════════════════════════════════════
    print("\n══ Step 2: Cleanup vendors (keep 5 most recent) ══")
    keep_vendor_rows = await conn.fetch(
        "SELECT id FROM vendors WHERE tenant_id = $1 ORDER BY created_at DESC LIMIT 5",
        tenant_id,
    )
    keep_vendor_ids = [r["id"] for r in keep_vendor_rows]

    # Must also handle FK references in POs, invoices, contract_vendors, etc.
    # Update existing POs/invoices that reference about-to-be-deleted vendors
    # by reassigning them to one of the kept vendors
    fallback_vendor = keep_vendor_ids[0]

    # Update POs referencing deleted vendors
    await conn.execute(
        "UPDATE purchase_orders SET vendor_id = $1 WHERE tenant_id = $2 AND vendor_id NOT IN (SELECT unnest($3::uuid[]))",
        fallback_vendor, tenant_id, keep_vendor_ids,
    )
    # Update invoices referencing deleted vendors
    await conn.execute(
        "UPDATE invoices SET vendor_id = $1 WHERE tenant_id = $2 AND vendor_id NOT IN (SELECT unnest($3::uuid[]))",
        fallback_vendor, tenant_id, keep_vendor_ids,
    )
    # Delete contract_vendors referencing deleted vendors
    await conn.execute(
        "DELETE FROM contract_vendors WHERE tenant_id = $1 AND vendor_id NOT IN (SELECT unnest($2::uuid[]))",
        tenant_id, keep_vendor_ids,
    )
    # Delete vendor_documents for deleted vendors
    await conn.execute(
        "DELETE FROM vendor_documents WHERE tenant_id = $1 AND vendor_id NOT IN (SELECT unnest($2::uuid[]))",
        tenant_id, keep_vendor_ids,
    )
    # Delete RFQ bids referencing deleted vendors
    await conn.execute(
        """DELETE FROM rfq_bids WHERE rfq_id IN (
             SELECT id FROM rfqs WHERE tenant_id = $1
           ) AND vendor_id NOT IN (SELECT unnest($2::uuid[]))""",
        tenant_id, keep_vendor_ids,
    )
    # (Users linked to vendors are by email, not FK — skip user deletion)
    del_v = await conn.execute(
        "DELETE FROM vendors WHERE tenant_id = $1 AND id NOT IN (SELECT unnest($2::uuid[]))",
        tenant_id, keep_vendor_ids,
    )
    print(f"  Kept {len(keep_vendor_ids)} vendors; deleted rest. {del_v}")

    # Ensure kept vendors are ACTIVE
    await conn.execute(
        "UPDATE vendors SET status = 'ACTIVE' WHERE id = ANY($1::uuid[])",
        keep_vendor_ids,
    )
    active_vendor_ids = keep_vendor_ids
    print(f"  Active vendors: {len(active_vendor_ids)}")

    # ═════════════════════════════════════════════════════════════
    # STEP 3: Generate 150 random PRs with line items
    # ═════════════════════════════════════════════════════════════
    print("\n══ Step 3: Generate 150 PRs ══")
    pr_ids = []
    for i in range(1, 151):
        pr_id = uuid.uuid4()
        requester = random.choice(user_ids)
        dept = random.choice(dept_ids)
        num_items = random.randint(1, 4)
        items = []
        total = 0
        for li in range(1, num_items + 1):
            qty = random.randint(1, 20)
            price = random.randint(500, 500000)  # 5.00 to 5000.00
            total += qty * price
            items.append((uuid.uuid4(), pr_id, li,
                          random.choice(LINE_ITEM_DESCS),
                          qty, price, None, None, datetime.utcnow()))

        created = datetime.utcnow() - timedelta(days=random.randint(0, 90))
        pr_number = f"PR-SEED-{uuid.uuid4().hex[:8].upper()}"
        desc = random.choice(PR_DESCRIPTIONS)

        await conn.execute("""
            INSERT INTO purchase_requests
            (id, tenant_id, pr_number, requester_id, department_id,
             status, total_cents, currency, description, justification,
             created_at, updated_at)
            VALUES ($1,$2,$3,$4,$5, 'PENDING',$6,'INR',$7,$8,$9,$9)
        """, pr_id, tenant_id, pr_number, requester, dept,
             total, desc, f"Seed justification #{i}", created)

        for item in items:
            await conn.execute("""
                INSERT INTO pr_line_items
                (id, pr_id, line_number, description, quantity,
                 unit_price_cents, category, notes, created_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
            """, *item)

        pr_ids.append(pr_id)
        if i % 50 == 0:
            print(f"  Created {i}/150 PRs")

    print(f"  ✅ Created {len(pr_ids)} PRs with line items")

    # ═════════════════════════════════════════════════════════════
    # STEP 4: Approve 124 PRs
    # ═════════════════════════════════════════════════════════════
    print("\n══ Step 4: Approve 124 PRs ══")
    approved_prs = pr_ids[:124]
    now = datetime.utcnow()
    for pr_id in approved_prs:
        await conn.execute(
            "UPDATE purchase_requests SET status='APPROVED', approved_at=$1, updated_at=$1 WHERE id=$2",
            now, pr_id,
        )
    # Keep remaining 26 as PENDING
    print(f"  ✅ Approved {len(approved_prs)} PRs (26 remain PENDING)")

    # ═════════════════════════════════════════════════════════════
    # STEP 5: Create 124 POs from approved PRs
    # ═════════════════════════════════════════════════════════════
    print("\n══ Step 5: Create 124 POs from approved PRs ══")
    po_ids = []
    po_vendor_map = {}
    for idx, pr_id in enumerate(approved_prs):
        po_id = uuid.uuid4()
        po_number = f"PO-SEED-{uuid.uuid4().hex[:8].upper()}"
        # Get PR total
        pr_total = await conn.fetchval(
            "SELECT total_cents FROM purchase_requests WHERE id = $1", pr_id
        )
        vendor = random.choice(active_vendor_ids) if idx < 100 else active_vendor_ids[0]
        delivery = date.today() + timedelta(days=random.randint(14, 90))
        created = datetime.utcnow() - timedelta(days=random.randint(0, 30))

        await conn.execute("""
            INSERT INTO purchase_orders
            (id, tenant_id, po_number, pr_id, vendor_id,
             status, total_cents, currency, expected_delivery_date,
             terms_and_conditions, issued_at, created_at, updated_at)
            VALUES ($1,$2,$3,$4,$5,
                    'ISSUED',$6,'INR',$7,
                    'Standard T&C apply',$8,$8,$8)
        """, po_id, tenant_id, po_number, pr_id, vendor,
             pr_total, delivery, created)

        # Copy PR line items to PO line items
        pr_items = await conn.fetch(
            "SELECT line_number, description, quantity, unit_price_cents FROM pr_line_items WHERE pr_id = $1",
            pr_id,
        )
        for item in pr_items:
            await conn.execute("""
                INSERT INTO po_line_items
                (id, po_id, line_number, description, quantity, unit_price_cents, received_quantity)
                VALUES ($1,$2,$3,$4,$5,$6,0)
            """, uuid.uuid4(), po_id, item["line_number"], item["description"],
                 item["quantity"], item["unit_price_cents"])

        po_ids.append(po_id)
        po_vendor_map[po_id] = vendor
        if (idx + 1) % 50 == 0:
            print(f"  Created {idx+1}/124 POs")

    print(f"  ✅ Created {len(po_ids)} POs (all ISSUED status)")

    # ═════════════════════════════════════════════════════════════
    # STEP 6: 100 POs already assigned to vendors (done above)
    # ═════════════════════════════════════════════════════════════
    print("\n══ Step 6: POs assigned to vendors ══")
    print(f"  ✅ 100 POs assigned to random active vendors, 24 to fallback vendor")

    # ═════════════════════════════════════════════════════════════
    # STEP 7: Acknowledge 85 POs from vendor side
    # ═════════════════════════════════════════════════════════════
    print("\n══ Step 7: Acknowledge 85 POs ══")
    ack_pos = po_ids[:85]
    for po_id in ack_pos:
        await conn.execute(
            "UPDATE purchase_orders SET status='ACKNOWLEDGED', updated_at=$1 WHERE id=$2",
            datetime.utcnow(), po_id,
        )
    print(f"  ✅ Acknowledged {len(ack_pos)} POs")

    # ═════════════════════════════════════════════════════════════
    # STEP 8: Upload invoices for 60 of the acknowledged POs
    # ═════════════════════════════════════════════════════════════
    print("\n══ Step 8: Create invoices for 60 POs ══")
    invoice_po_ids = ack_pos[:60]
    invoice_ids = []
    for idx, po_id in enumerate(invoice_po_ids):
        inv_id = uuid.uuid4()
        inv_number = f"INV-SEED-{uuid.uuid4().hex[:8].upper()}"
        vendor_id = po_vendor_map[po_id]
        po_total = await conn.fetchval(
            "SELECT total_cents FROM purchase_orders WHERE id = $1", po_id
        )
        inv_date = date.today() - timedelta(days=random.randint(0, 30))
        due = inv_date + timedelta(days=30)
        created = datetime.utcnow() - timedelta(days=random.randint(0, 15))

        await conn.execute("""
            INSERT INTO invoices
            (id, tenant_id, invoice_number, po_id, vendor_id,
             status, invoice_date, due_date, total_cents, currency,
             document_url, ocr_status, created_at, updated_at)
            VALUES ($1,$2,$3,$4,$5,
                    'UPLOADED',$6,$7,$8,'INR',
                    'https://storage.example.com/invoices/sample.pdf','SKIPPED',$9,$9)
        """, inv_id, tenant_id, inv_number, po_id, vendor_id,
             inv_date, due, po_total, created)

        # Copy line items from PO
        po_items = await conn.fetch(
            "SELECT line_number, description, quantity, unit_price_cents FROM po_line_items WHERE po_id = $1",
            po_id,
        )
        for item in po_items:
            await conn.execute("""
                INSERT INTO invoice_line_items
                (id, invoice_id, line_number, description, quantity, unit_price_cents)
                VALUES ($1,$2,$3,$4,$5,$6)
            """, uuid.uuid4(), inv_id, item["line_number"], item["description"],
                 item["quantity"], item["unit_price_cents"])

        invoice_ids.append(inv_id)
        if (idx + 1) % 20 == 0:
            print(f"  Created {idx+1}/60 invoices")

    print(f"  ✅ Created {len(invoice_ids)} invoices (status: UPLOADED)")

    # ═════════════════════════════════════════════════════════════
    # STEP 9: Approve 45 invoices, raise exception on 10
    # ═════════════════════════════════════════════════════════════
    print("\n══ Step 9: Process invoices ══")
    # Approve 45
    approved_invoices = invoice_ids[:45]
    for inv_id in approved_invoices:
        await conn.execute(
            "UPDATE invoices SET status='APPROVED', match_status='PASS', approved_payment_at=$1, updated_at=$1 WHERE id=$2",
            datetime.utcnow(), inv_id,
        )
    print(f"  ✅ Approved {len(approved_invoices)} invoices")

    # Raise exception on 10
    exception_invoices = invoice_ids[45:55]
    for inv_id in exception_invoices:
        await conn.execute("""
            UPDATE invoices SET status='DISPUTED', match_status='FAIL',
            match_exceptions = $1::jsonb, updated_at=$2 WHERE id=$3
        """,
            '{"reason": "Amount mismatch detected during manual review", "raised_by": "admin"}',
            datetime.utcnow(), inv_id,
        )
    print(f"  ✅ Raised exception on {len(exception_invoices)} invoices")

    # Remaining 5 invoices stay as UPLOADED
    remaining = len(invoice_ids) - 45 - 10
    print(f"  📋 {remaining} invoices remain as UPLOADED")

    # ═════════════════════════════════════════════════════════════
    # SUMMARY
    # ═════════════════════════════════════════════════════════════
    print("\n" + "═" * 55)
    print("  SEED COMPLETE — Final Summary")
    print("═" * 55)

    for table, label in [
        ("contracts", "Contracts"),
        ("vendors", "Vendors"),
        ("purchase_requests", "Purchase Requests"),
        ("purchase_orders", "Purchase Orders"),
        ("invoices", "Invoices"),
    ]:
        count = await conn.fetchval(
            f"SELECT count(*) FROM {table} WHERE tenant_id = $1", tenant_id
        )
        print(f"  {label:25s}: {count}")

    # Status breakdown for PRs
    pr_stats = await conn.fetch(
        "SELECT status, count(*) as c FROM purchase_requests WHERE tenant_id = $1 GROUP BY status ORDER BY status",
        tenant_id,
    )
    print("\n  PR Status Breakdown:")
    for r in pr_stats:
        print(f"    {r['status']:20s}: {r['c']}")

    po_stats = await conn.fetch(
        "SELECT status, count(*) as c FROM purchase_orders WHERE tenant_id = $1 GROUP BY status ORDER BY status",
        tenant_id,
    )
    print("\n  PO Status Breakdown:")
    for r in po_stats:
        print(f"    {r['status']:20s}: {r['c']}")

    inv_stats = await conn.fetch(
        "SELECT status, count(*) as c FROM invoices WHERE tenant_id = $1 GROUP BY status ORDER BY status",
        tenant_id,
    )
    print("\n  Invoice Status Breakdown:")
    for r in inv_stats:
        print(f"    {r['status']:20s}: {r['c']}")

    await conn.close()
    print("\n✅ Done!")


if __name__ == "__main__":
    asyncio.run(main())
