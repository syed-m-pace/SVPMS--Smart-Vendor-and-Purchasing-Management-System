"""
Comprehensive data seeding script for SVPMS — 2-year historical data.
Distributes records across Feb 2024 → Feb 2026 for realistic dashboard charts.

Operations:
  1. Clean up old seeded data (contracts → 5, vendors → 5, remove seeded PRs/POs/invoices)
  2. Seed budgets for all 8+ quarters
  3. Generate 150 PRs spread over 2 years (with line items)
  4. Approve 124 PRs
  5. Create 124 POs from approved PRs
  6. Assign 100 POs to random active vendors
  7. Acknowledge 85 POs from vendor side
  8. Upload invoices for 60 acknowledged POs
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


# ── Configuration ────────────────────────────────────────────────
TIMELINE_START = datetime(2024, 2, 1)   # Feb 2024
TIMELINE_END = datetime(2026, 2, 27)    # Feb 2026

NUM_PRS = 150
NUM_APPROVE = 124
NUM_ACKNOWLEDGE = 85
NUM_INVOICES = 60
NUM_INVOICE_APPROVE = 45
NUM_INVOICE_EXCEPTION = 10

KEEP_CONTRACTS = 5
KEEP_VENDORS = 5


# ── Connection ───────────────────────────────────────────────────
def _get_dsn() -> str:
    url = settings.DATABASE_URL
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    url = url.replace("?sslmode=require", "").replace("&sslmode=require", "")
    return url


def random_date_between(start: datetime, end: datetime) -> datetime:
    """Return a random datetime between start and end."""
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)


def spread_dates(n: int, start: datetime, end: datetime) -> list:
    """Generate n sorted random dates spread across start..end."""
    dates = [random_date_between(start, end) for _ in range(n)]
    dates.sort()
    return dates


# ── Realistic data ───────────────────────────────────────────────
PR_DESCRIPTIONS = [
    "Office supplies for quarterly restock",
    "Server hardware refresh - data center",
    "Cloud hosting annual renewal - AWS/GCP",
    "Marketing campaign materials - Q campaign",
    "Employee training & certification program",
    "Software licenses renewal - enterprise suite",
    "Data center maintenance & cooling upgrade",
    "Network infrastructure - switch/router upgrade",
    "Security audit tooling & penetration testing",
    "HR onboarding kits for new hires",
    "Furniture procurement for new office wing",
    "Travel equipment - laptops & accessories",
    "Lab equipment for R&D department",
    "Conference room AV setup - 4K displays",
    "Warehouse packing & shipping supplies",
    "Annual subscription - SaaS tools",
    "Vehicle fleet maintenance contract",
    "Catering services - corporate events",
    "Cleaning & janitorial supplies",
    "Safety equipment - PPE & first aid kits",
]

LINE_ITEM_DESCS = [
    "Laptop Dell XPS 15 16GB/512GB", "Monitor 27-inch 4K IPS",
    "Mechanical Keyboard Cherry MX", "Wireless Mouse Logitech MX3",
    "USB-C Hub 10-port", "Standing Desk Adjustable", "Ergonomic Office Chair",
    "Whiteboard 6ft Magnetic", "Webcam Logitech 4K Pro", "Headset NC Jabra Evolve2",
    "Server Rack 42U", "SSD 1TB NVMe Samsung", "RAM 32GB DDR5 Kit",
    "Ethernet Cable Cat6A 100ft", "UPS 1500VA APC", "Laser Printer HP Color",
    "Flatbed Scanner A3", "External HDD 4TB Seagate", "Projector 4K BenQ",
    "Conference Phone Poly Trio", "Firewall Appliance FortiGate",
    "Access Point WiFi 6E", "KVM Switch 8-port", "Cable Management Kit",
    "Thermal Paste & Cleaning Kit", "Server PSU 750W Redundant",
    "GPU NVIDIA A100 40GB", "NAS Synology 8-bay", "Tape Backup LTO-9",
    "PDU Managed 16-outlet",
]


async def main():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    conn = await asyncpg.connect(_get_dsn(), ssl=ctx)

    # ── Resolve tenant + user ────────────────────────────────────
    tenant_id = await conn.fetchval("SELECT id FROM tenants LIMIT 1")
    await conn.execute(
        "SELECT set_config('app.current_tenant_id', $1, false)", str(tenant_id),
    )
    admin_user = await conn.fetchval(
        "SELECT id FROM users WHERE tenant_id = $1 AND role = 'admin' LIMIT 1", tenant_id,
    )
    dept_rows = await conn.fetch(
        "SELECT id, name FROM departments WHERE tenant_id = $1 AND name NOT LIKE 'Concur%%'", tenant_id,
    )
    dept_ids = [r["id"] for r in dept_rows]
    dept_names = {str(r["id"]): r["name"] for r in dept_rows}
    user_rows = await conn.fetch(
        "SELECT id FROM users WHERE tenant_id = $1 AND role != 'vendor'", tenant_id,
    )
    user_ids = [r["id"] for r in user_rows]

    print(f"Tenant: {tenant_id}")
    print(f"Admin: {admin_user}")
    print(f"Departments: {len(dept_ids)} — {list(dept_names.values())}")
    print(f"Users (non-vendor): {len(user_ids)}")
    print(f"Timeline: {TIMELINE_START.date()} → {TIMELINE_END.date()}")

    # ═════════════════════════════════════════════════════════════
    # STEP 0: Clean up previously seeded data
    # ═════════════════════════════════════════════════════════════
    print("\n══ Step 0: Cleanup previously seeded data ══")

    # Delete seeded invoice line items + invoices
    await conn.execute("""
        DELETE FROM invoice_line_items
        WHERE invoice_id IN (SELECT id FROM invoices WHERE tenant_id = $1 AND invoice_number LIKE 'INV-SEED-%%')
    """, tenant_id)
    del_inv = await conn.execute(
        "DELETE FROM invoices WHERE tenant_id = $1 AND invoice_number LIKE 'INV-SEED-%%'", tenant_id,
    )
    print(f"  Deleted seeded invoices: {del_inv}")

    # Delete seeded PO line items + POs
    await conn.execute("""
        DELETE FROM po_line_items
        WHERE po_id IN (SELECT id FROM purchase_orders WHERE tenant_id = $1 AND po_number LIKE 'PO-SEED-%%')
    """, tenant_id)
    del_po = await conn.execute(
        "DELETE FROM purchase_orders WHERE tenant_id = $1 AND po_number LIKE 'PO-SEED-%%'", tenant_id,
    )
    print(f"  Deleted seeded POs: {del_po}")

    # Delete seeded PR line items + PRs
    await conn.execute("""
        DELETE FROM pr_line_items
        WHERE pr_id IN (SELECT id FROM purchase_requests WHERE tenant_id = $1 AND pr_number LIKE 'PR-SEED-%%')
    """, tenant_id)
    del_pr = await conn.execute(
        "DELETE FROM purchase_requests WHERE tenant_id = $1 AND pr_number LIKE 'PR-SEED-%%'", tenant_id,
    )
    print(f"  Deleted seeded PRs: {del_pr}")

    # Delete seeded budgets (keep original ones)
    del_bud = await conn.execute(
        "DELETE FROM budgets WHERE tenant_id = $1 AND (fiscal_year < 2024 OR fiscal_year > 2027 OR CAST(id AS text) NOT LIKE 'b0000000-%%')",
        tenant_id,
    )
    print(f"  Deleted extra budgets: {del_bud}")

    # Contracts cleanup: keep 5 random
    keep_ids = await conn.fetch(
        "SELECT id FROM contracts WHERE tenant_id = $1 ORDER BY random() LIMIT $2",
        tenant_id, KEEP_CONTRACTS,
    )
    keep_contract_ids = [r["id"] for r in keep_ids]
    await conn.execute(
        "DELETE FROM contract_vendors WHERE tenant_id = $1 AND contract_id NOT IN (SELECT unnest($2::uuid[]))",
        tenant_id, keep_contract_ids,
    )
    del_c = await conn.execute(
        "DELETE FROM contracts WHERE tenant_id = $1 AND id NOT IN (SELECT unnest($2::uuid[]))",
        tenant_id, keep_contract_ids,
    )
    print(f"  Contracts: kept {len(keep_contract_ids)}, deleted {del_c}")

    # Vendors cleanup: keep 5 most recent
    keep_vendor_rows = await conn.fetch(
        "SELECT id FROM vendors WHERE tenant_id = $1 ORDER BY created_at DESC LIMIT $2",
        tenant_id, KEEP_VENDORS,
    )
    keep_vendor_ids = [r["id"] for r in keep_vendor_rows]
    fallback_vendor = keep_vendor_ids[0]
    await conn.execute(
        "UPDATE purchase_orders SET vendor_id = $1 WHERE tenant_id = $2 AND vendor_id NOT IN (SELECT unnest($3::uuid[]))",
        fallback_vendor, tenant_id, keep_vendor_ids,
    )
    await conn.execute(
        "UPDATE invoices SET vendor_id = $1 WHERE tenant_id = $2 AND vendor_id NOT IN (SELECT unnest($3::uuid[]))",
        fallback_vendor, tenant_id, keep_vendor_ids,
    )
    await conn.execute(
        "DELETE FROM contract_vendors WHERE tenant_id = $1 AND vendor_id NOT IN (SELECT unnest($2::uuid[]))",
        tenant_id, keep_vendor_ids,
    )
    await conn.execute(
        "DELETE FROM vendor_documents WHERE tenant_id = $1 AND vendor_id NOT IN (SELECT unnest($2::uuid[]))",
        tenant_id, keep_vendor_ids,
    )
    await conn.execute("""
        DELETE FROM rfq_bids WHERE rfq_id IN (
            SELECT id FROM rfqs WHERE tenant_id = $1
        ) AND vendor_id NOT IN (SELECT unnest($2::uuid[]))
    """, tenant_id, keep_vendor_ids)
    del_v = await conn.execute(
        "DELETE FROM vendors WHERE tenant_id = $1 AND id NOT IN (SELECT unnest($2::uuid[]))",
        tenant_id, keep_vendor_ids,
    )
    await conn.execute(
        "UPDATE vendors SET status = 'ACTIVE' WHERE id = ANY($1::uuid[])", keep_vendor_ids,
    )
    active_vendor_ids = keep_vendor_ids
    print(f"  Vendors: kept {len(keep_vendor_ids)} (all ACTIVE), deleted {del_v}")

    # ═════════════════════════════════════════════════════════════
    # STEP 1: Seed budgets for 8 quarters (Q1 2024 → Q4 2025 + Q1 2026)
    # ═════════════════════════════════════════════════════════════
    print("\n══ Step 1: Seed quarterly budgets (8 quarters × depts) ══")
    quarters = [
        (2024, 1), (2024, 2), (2024, 3), (2024, 4),
        (2025, 1), (2025, 2), (2025, 3), (2025, 4),
        (2026, 1),
    ]
    for fy, q in quarters:
        for dept_id in dept_ids:
            # Check if budget already exists
            existing = await conn.fetchval(
                "SELECT id FROM budgets WHERE tenant_id=$1 AND department_id=$2 AND fiscal_year=$3 AND quarter=$4",
                tenant_id, dept_id, fy, q,
            )
            if existing:
                continue
            total = random.randint(200000_00, 5000000_00)  # ₹2L – ₹50L
            # Older quarters: higher spend pct; current quarter: lower
            if fy < 2026:
                spent_pct = random.uniform(0.50, 0.95)
            else:
                spent_pct = random.uniform(0.15, 0.45)
            spent = int(total * spent_pct)
            await conn.execute("""
                INSERT INTO budgets (id, tenant_id, department_id, fiscal_year, quarter,
                    total_cents, spent_cents, currency, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, 'INR', $8, $8)
            """, uuid.uuid4(), tenant_id, dept_id, fy, q, total, spent,
                 datetime(fy, (q - 1) * 3 + 1, 1))  # created at start of quarter
    budget_count = await conn.fetchval("SELECT count(*) FROM budgets WHERE tenant_id=$1", tenant_id)
    print(f"  Total budgets now: {budget_count}")

    # ═════════════════════════════════════════════════════════════
    # STEP 2: Generate 150 random PRs spread over 2 years
    # ═════════════════════════════════════════════════════════════
    print(f"\n══ Step 2: Generate {NUM_PRS} PRs (spread over 2 years) ══")
    pr_dates = spread_dates(NUM_PRS, TIMELINE_START, TIMELINE_END)
    pr_ids = []
    pr_date_map = {}
    pr_dept_map = {}

    for i, created in enumerate(pr_dates, 1):
        pr_id = uuid.uuid4()
        requester = random.choice(user_ids)
        dept = random.choice(dept_ids)
        num_items = random.randint(1, 4)
        total = 0
        items = []
        for li in range(1, num_items + 1):
            qty = random.randint(1, 20)
            price = random.randint(500, 500000)  # ₹5 – ₹5000
            total += qty * price
            items.append((uuid.uuid4(), pr_id, li,
                          random.choice(LINE_ITEM_DESCS),
                          qty, price, None, None, created))

        pr_number = f"PR-SEED-{uuid.uuid4().hex[:8].upper()}"
        desc = random.choice(PR_DESCRIPTIONS)

        await conn.execute("""
            INSERT INTO purchase_requests
            (id, tenant_id, pr_number, requester_id, department_id,
             status, total_cents, currency, description, justification,
             created_at, updated_at)
            VALUES ($1,$2,$3,$4,$5, 'PENDING',$6,'INR',$7,$8,$9,$9)
        """, pr_id, tenant_id, pr_number, requester, dept,
             total, desc, f"Business justification - {desc}", created)

        for item in items:
            await conn.execute("""
                INSERT INTO pr_line_items
                (id, pr_id, line_number, description, quantity,
                 unit_price_cents, category, notes, created_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
            """, *item)

        pr_ids.append(pr_id)
        pr_date_map[pr_id] = created
        pr_dept_map[pr_id] = dept
        if i % 50 == 0:
            print(f"  Created {i}/{NUM_PRS} PRs (latest: {created.date()})")

    print(f"  ✅ Created {len(pr_ids)} PRs with line items")

    # ═════════════════════════════════════════════════════════════
    # STEP 3: Approve 124 PRs (1–3 days after creation)
    # ═════════════════════════════════════════════════════════════
    print(f"\n══ Step 3: Approve {NUM_APPROVE} PRs ══")
    approved_prs = pr_ids[:NUM_APPROVE]
    for pr_id in approved_prs:
        approved_at = pr_date_map[pr_id] + timedelta(days=random.randint(1, 3))
        await conn.execute(
            "UPDATE purchase_requests SET status='APPROVED', approved_at=$1, submitted_at=$2, updated_at=$1 WHERE id=$3",
            approved_at, pr_date_map[pr_id] + timedelta(hours=random.randint(1, 12)), pr_id,
        )
    remaining = NUM_PRS - NUM_APPROVE
    print(f"  ✅ Approved {len(approved_prs)} PRs ({remaining} remain PENDING)")

    # ═════════════════════════════════════════════════════════════
    # STEP 4: Create 124 POs from approved PRs (2–7 days after approval)
    # ═════════════════════════════════════════════════════════════
    print(f"\n══ Step 4: Create {NUM_APPROVE} POs from approved PRs ══")
    po_ids = []
    po_vendor_map = {}
    po_date_map = {}

    for idx, pr_id in enumerate(approved_prs):
        po_id = uuid.uuid4()
        po_number = f"PO-SEED-{uuid.uuid4().hex[:8].upper()}"
        pr_total = await conn.fetchval(
            "SELECT total_cents FROM purchase_requests WHERE id = $1", pr_id,
        )
        vendor = random.choice(active_vendor_ids) if idx < 100 else active_vendor_ids[0]
        pr_approved = pr_date_map[pr_id] + timedelta(days=random.randint(1, 3))
        po_created = pr_approved + timedelta(days=random.randint(2, 7))
        delivery = po_created.date() + timedelta(days=random.randint(14, 90))

        await conn.execute("""
            INSERT INTO purchase_orders
            (id, tenant_id, po_number, pr_id, vendor_id,
             status, total_cents, currency, expected_delivery_date,
             terms_and_conditions, issued_at, created_at, updated_at)
            VALUES ($1,$2,$3,$4,$5,
                    'ISSUED',$6,'INR',$7,
                    'Standard T&C apply. Net 30 payment terms.',$8,$8,$8)
        """, po_id, tenant_id, po_number, pr_id, vendor,
             pr_total, delivery, po_created)

        # Copy PR line items to PO
        pr_items = await conn.fetch(
            "SELECT line_number, description, quantity, unit_price_cents FROM pr_line_items WHERE pr_id=$1", pr_id,
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
        po_date_map[po_id] = po_created
        if (idx + 1) % 50 == 0:
            print(f"  Created {idx+1}/{NUM_APPROVE} POs")

    print(f"  ✅ Created {len(po_ids)} POs (100 random vendors, 24 to first vendor)")

    # ═════════════════════════════════════════════════════════════
    # STEP 5: Acknowledge 85 POs (3–10 days after issuance)
    # ═════════════════════════════════════════════════════════════
    print(f"\n══ Step 5: Acknowledge {NUM_ACKNOWLEDGE} POs ══")
    ack_pos = po_ids[:NUM_ACKNOWLEDGE]
    for po_id in ack_pos:
        ack_date = po_date_map[po_id] + timedelta(days=random.randint(3, 10))
        await conn.execute(
            "UPDATE purchase_orders SET status='ACKNOWLEDGED', updated_at=$1 WHERE id=$2",
            ack_date, po_id,
        )
    print(f"  ✅ Acknowledged {len(ack_pos)} POs")

    # ═════════════════════════════════════════════════════════════
    # STEP 6: Create invoices for 60 acknowledged POs (7–30 days after ack)
    # ═════════════════════════════════════════════════════════════
    print(f"\n══ Step 6: Create {NUM_INVOICES} invoices ══")
    invoice_po_ids = ack_pos[:NUM_INVOICES]
    invoice_ids = []
    invoice_date_map = {}

    for idx, po_id in enumerate(invoice_po_ids):
        inv_id = uuid.uuid4()
        inv_number = f"INV-SEED-{uuid.uuid4().hex[:8].upper()}"
        vendor_id = po_vendor_map[po_id]
        po_total = await conn.fetchval(
            "SELECT total_cents FROM purchase_orders WHERE id = $1", po_id,
        )
        po_date = po_date_map[po_id]
        inv_created = po_date + timedelta(days=random.randint(7, 30))
        inv_date = inv_created.date()
        due = inv_date + timedelta(days=30)

        await conn.execute("""
            INSERT INTO invoices
            (id, tenant_id, invoice_number, po_id, vendor_id,
             status, invoice_date, due_date, total_cents, currency,
             document_url, ocr_status, created_at, updated_at)
            VALUES ($1,$2,$3,$4,$5,
                    'UPLOADED',$6,$7,$8,'INR',
                    'https://storage.example.com/invoices/sample.pdf','SKIPPED',$9,$9)
        """, inv_id, tenant_id, inv_number, po_id, vendor_id,
             inv_date, due, po_total, inv_created)

        # Copy PO line items to invoice
        po_items = await conn.fetch(
            "SELECT line_number, description, quantity, unit_price_cents FROM po_line_items WHERE po_id=$1", po_id,
        )
        for item in po_items:
            await conn.execute("""
                INSERT INTO invoice_line_items
                (id, invoice_id, line_number, description, quantity, unit_price_cents)
                VALUES ($1,$2,$3,$4,$5,$6)
            """, uuid.uuid4(), inv_id, item["line_number"], item["description"],
                 item["quantity"], item["unit_price_cents"])

        invoice_ids.append(inv_id)
        invoice_date_map[inv_id] = inv_created
        if (idx + 1) % 20 == 0:
            print(f"  Created {idx+1}/{NUM_INVOICES} invoices")

    print(f"  ✅ Created {len(invoice_ids)} invoices (status: UPLOADED)")

    # ═════════════════════════════════════════════════════════════
    # STEP 7: Approve 45 invoices, raise exception on 10
    # ═════════════════════════════════════════════════════════════
    print(f"\n══ Step 7: Process invoices ══")
    approved_invoices = invoice_ids[:NUM_INVOICE_APPROVE]
    for inv_id in approved_invoices:
        approved_at = invoice_date_map[inv_id] + timedelta(days=random.randint(2, 7))
        await conn.execute(
            "UPDATE invoices SET status='APPROVED', match_status='PASS', approved_payment_at=$1, updated_at=$1 WHERE id=$2",
            approved_at, inv_id,
        )
    print(f"  ✅ Approved {len(approved_invoices)} invoices")

    exception_invoices = invoice_ids[NUM_INVOICE_APPROVE:NUM_INVOICE_APPROVE + NUM_INVOICE_EXCEPTION]
    for inv_id in exception_invoices:
        exc_date = invoice_date_map[inv_id] + timedelta(days=random.randint(1, 5))
        await conn.execute("""
            UPDATE invoices SET status='DISPUTED', match_status='FAIL',
            match_exceptions = $1::jsonb, updated_at=$2 WHERE id=$3
        """,
            '{"reason": "Amount mismatch detected during 3-way matching", "raised_by": "system"}',
            exc_date, inv_id,
        )
    print(f"  ✅ Raised exception on {len(exception_invoices)} invoices")
    print(f"  📋 {len(invoice_ids) - NUM_INVOICE_APPROVE - NUM_INVOICE_EXCEPTION} invoices remain UPLOADED")

    # ═════════════════════════════════════════════════════════════
    # SUMMARY
    # ═════════════════════════════════════════════════════════════
    print("\n" + "═" * 60)
    print("  SEED COMPLETE — Final Summary (2-year historical data)")
    print("═" * 60)

    for table, label in [
        ("contracts", "Contracts"),
        ("vendors", "Vendors"),
        ("budgets", "Budgets"),
        ("purchase_requests", "Purchase Requests"),
        ("purchase_orders", "Purchase Orders"),
        ("invoices", "Invoices"),
    ]:
        count = await conn.fetchval(f"SELECT count(*) FROM {table} WHERE tenant_id=$1", tenant_id)
        print(f"  {label:25s}: {count}")

    # Status breakdowns
    for table, label in [
        ("purchase_requests", "PR"),
        ("purchase_orders", "PO"),
        ("invoices", "Invoice"),
    ]:
        rows = await conn.fetch(
            f"SELECT status, count(*) as c FROM {table} WHERE tenant_id=$1 GROUP BY status ORDER BY status",
            tenant_id,
        )
        print(f"\n  {label} Status Breakdown:")
        for r in rows:
            print(f"    {r['status']:20s}: {r['c']}")

    # Date range check
    pr_range = await conn.fetchrow(
        "SELECT min(created_at) as mn, max(created_at) as mx FROM purchase_requests WHERE tenant_id=$1 AND pr_number LIKE 'PR-SEED-%%'",
        tenant_id,
    )
    print(f"\n  PR date range: {pr_range['mn'].date()} → {pr_range['mx'].date()}")

    inv_range = await conn.fetchrow(
        "SELECT min(created_at) as mn, max(created_at) as mx FROM invoices WHERE tenant_id=$1 AND invoice_number LIKE 'INV-SEED-%%'",
        tenant_id,
    )
    if inv_range and inv_range['mn']:
        print(f"  Invoice date range: {inv_range['mn'].date()} → {inv_range['mx'].date()}")

    await conn.close()
    print("\n✅ Done!")


if __name__ == "__main__":
    asyncio.run(main())
