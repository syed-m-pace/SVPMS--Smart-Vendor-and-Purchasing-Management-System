"""
Seed 250 random Contract records using raw asyncpg (bypasses SQLAlchemy).
Run:  source .venv/bin/activate && PYTHONPATH=. python scripts/seed_contracts.py
"""
import asyncio
import uuid
import random
import ssl
from datetime import datetime, timedelta, date

import asyncpg
from api.config import settings

# ── Connection ────────────────────────────────────────────────────
def _get_dsn() -> str:
    """Convert SQLAlchemy-style URL to asyncpg DSN."""
    url = settings.DATABASE_URL
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    url = url.replace("?sslmode=require", "").replace("&sslmode=require", "")
    return url


# ── Data generators ──────────────────────────────────────────────
TITLES = [
    "Master Services Agreement", "Non-Disclosure Agreement",
    "Software Licensing Agreement", "SaaS Subscription Contract",
    "Maintenance & Support Agreement", "Professional Services Contract",
    "Hardware Supply Agreement", "Data Processing Agreement",
    "IT Outsourcing Contract", "Cloud Infrastructure Agreement",
    "Annual Procurement Contract", "Consulting Services Agreement",
    "Staffing Services Agreement", "Facility Management Contract",
    "Logistics & Shipping Agreement", "Marketing Services Contract",
    "Quality Assurance Agreement", "Security Services Contract",
    "Training & Development Agreement", "Equipment Lease Agreement",
]

SLA_TERMS = [
    "99.9% uptime SLA with 4-hour response time for critical issues.",
    "Monthly reporting with quarterly business reviews.",
    "24/7 support with P1 issues resolved within 2 hours.",
    "Dedicated account manager and escalation matrix provided.",
    "Annual performance review with penalty clauses for SLA breaches.",
    None,
]

STATUSES = ["DRAFT", "ACTIVE", "EXPIRED", "TERMINATED"]
STATUS_WEIGHTS = [0.15, 0.55, 0.20, 0.10]
CURRENCIES = ["INR", "USD", "EUR"]


def gen(tenant_id: uuid.UUID, seq: int) -> tuple:
    status = random.choices(STATUSES, weights=STATUS_WEIGHTS, k=1)[0]
    start = datetime.utcnow() - timedelta(days=random.randint(0, 730))
    end = start + timedelta(days=random.randint(90, 1095))
    terminated_at = None
    if status == "TERMINATED":
        terminated_at = start + timedelta(days=random.randint(30, (end - start).days))
    value_cents = random.choice([None, random.randint(50000, 50_000_000)])
    return (
        uuid.uuid4(),                                  # id
        tenant_id,                                     # tenant_id
        f"SEED-{uuid.uuid4().hex[:8].upper()}",        # contract_number
        None,                                          # vendor_id  (Master)
        None,                                          # po_id
        f"{random.choice(TITLES)} #{seq}",             # title
        f"Auto-generated seed contract #{seq}.",       # description
        status,                                        # status
        value_cents,                                   # value_cents
        random.choice(CURRENCIES),                     # currency
        start.date(),                                  # start_date
        end.date(),                                    # end_date
        random.choice([True, False]),                  # auto_renew
        random.choice([30, 60, 90]),                   # renewal_notice_days
        random.choice(SLA_TERMS),                      # sla_terms
        None,                                          # document_key
        terminated_at,                                 # terminated_at
        start,                                         # created_at
        start,                                         # updated_at
    )


# ── Main ─────────────────────────────────────────────────────────
async def main():
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    conn = await asyncpg.connect(_get_dsn(), ssl=ssl_ctx)

    # Get tenant
    row = await conn.fetchrow("SELECT id FROM tenants LIMIT 1")
    if not row:
        print("ERROR: No tenants in DB.")
        return
    tenant_id = row["id"]
    print(f"Using tenant: {tenant_id}")

    # Set RLS context
    await conn.execute("SELECT set_config('app.current_tenant_id', $1, false)", str(tenant_id))

    # Get an admin user to use as `created_by`
    user_row = await conn.fetchrow(
        "SELECT id FROM users WHERE tenant_id = $1 AND role = 'admin' LIMIT 1", tenant_id
    )
    if not user_row:
        user_row = await conn.fetchrow("SELECT id FROM users WHERE tenant_id = $1 LIMIT 1", tenant_id)
    if not user_row:
        print("ERROR: No users found for this tenant.")
        return
    created_by = user_row["id"]
    print(f"Using created_by user: {created_by}")

    sql = """
        INSERT INTO contracts (
            id, tenant_id, contract_number, vendor_id, po_id,
            title, description, status, value_cents, currency,
            start_date, end_date, auto_renew, renewal_notice_days,
            sla_terms, document_key, terminated_at, created_at, updated_at,
            created_by
        ) VALUES (
            $1, $2, $3, $4, $5,
            $6, $7, $8, $9, $10,
            $11, $12, $13, $14,
            $15, $16, $17, $18, $19,
            $20
        )
    """

    count = 250
    inserted = 0
    for i in range(1, count + 1):
        data = gen(tenant_id, i)
        try:
            await conn.execute(sql, *data, created_by)
            inserted += 1
        except Exception as e:
            print(f"  FAIL #{i}: {e}")
        if i % 50 == 0:
            print(f"  Progress: {i}/{count}")

    await conn.close()
    print(f"\n✅  Done. Inserted {inserted}/{count} contracts.")


if __name__ == "__main__":
    asyncio.run(main())
