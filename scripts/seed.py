"""
Seed script for SVPMS Phase 2: creates tenants, departments, users, budgets, vendors.
Run from SVPMS_V4/: python -m scripts.seed
"""
import asyncio
import sys
import os
import uuid

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, select
from api.database import AsyncSessionLocal, engine
from api.models.tenant import Tenant
from api.models.user import User
from api.models.department import Department
from api.models.budget import Budget
from api.models.vendor import Vendor
from api.services.auth_service import hash_password

# ---------- Fixed UUIDs ----------

TENANT_ACME_ID = uuid.UUID("a0000000-0000-0000-0000-000000000001")
TENANT_BETA_ID = uuid.UUID("b0000000-0000-0000-0000-000000000002")

DEPT_ENGINEERING_ID = uuid.UUID("d0000000-0000-0000-0000-000000000001")
DEPT_MARKETING_ID = uuid.UUID("d0000000-0000-0000-0000-000000000002")
DEPT_OPERATIONS_ID = uuid.UUID("d0000000-0000-0000-0000-000000000003")
DEPT_FINANCE_ID = uuid.UUID("d0000000-0000-0000-0000-000000000004")

USER_ADMIN_ID = uuid.UUID("u0000000-0000-0000-0000-000000000001".replace("u", "a"))
USER_ENG_MGR_ID = uuid.UUID("a0000000-0000-0000-0000-000000000102")
USER_FINANCE_ID = uuid.UUID("a0000000-0000-0000-0000-000000000103")
USER_FINANCE_HEAD_ID = uuid.UUID("a0000000-0000-0000-0000-000000000104")
USER_CFO_ID = uuid.UUID("a0000000-0000-0000-0000-000000000105")
USER_PROCUREMENT_ID = uuid.UUID("a0000000-0000-0000-0000-000000000106")
USER_PROC_LEAD_ID = uuid.UUID("a0000000-0000-0000-0000-000000000107")
USER_VENDOR_ID = uuid.UUID("a0000000-0000-0000-0000-000000000108")
USER_MKT_MGR_ID = uuid.UUID("a0000000-0000-0000-0000-000000000109")
USER_OPS_MGR_ID = uuid.UUID("a0000000-0000-0000-0000-000000000110")

BUDGET_ENG_ID = uuid.UUID("b0000000-0000-0000-0000-000000000101")
BUDGET_MKT_ID = uuid.UUID("b0000000-0000-0000-0000-000000000102")
BUDGET_OPS_ID = uuid.UUID("b0000000-0000-0000-0000-000000000103")
BUDGET_FIN_ID = uuid.UUID("b0000000-0000-0000-0000-000000000104")

VENDOR_ALPHA_ID = uuid.UUID("e0000000-0000-0000-0000-000000000001")
VENDOR_BETA_ID = uuid.UUID("e0000000-0000-0000-0000-000000000002")
VENDOR_GAMMA_ID = uuid.UUID("e0000000-0000-0000-0000-000000000003")
VENDOR_DELTA_ID = uuid.UUID("e0000000-0000-0000-0000-000000000004")
VENDOR_OMEGA_ID = uuid.UUID("e0000000-0000-0000-0000-000000000005")

DEFAULT_PASSWORD = "SvpmsTest123!"


async def seed():
    async with AsyncSessionLocal() as db:
        # Bypass RLS for seeding — use superuser connection (no tenant context needed for INSERTs when RLS USING policy is set)
        # We need to disable RLS temporarily or use a role that bypasses it.
        # Since we're the DB owner, RLS doesn't apply to table owners by default in Postgres.

        # Check if already seeded
        result = await db.execute(select(Tenant).where(Tenant.id == TENANT_ACME_ID))
        if result.scalar_one_or_none():
            print("Seed data already exists. Skipping.")
            return

        hashed_pw = hash_password(DEFAULT_PASSWORD)

        # --- Tenants ---
        tenants = [
            Tenant(
                id=TENANT_ACME_ID,
                name="Acme Corporation",
                slug="acme-corp",
                status="ACTIVE",
                settings={"currency": "INR", "price_tolerance_pct": 2.0, "min_variance_cents": 1000},
            ),
            Tenant(
                id=TENANT_BETA_ID,
                name="Beta Industries",
                slug="beta-inc",
                status="ACTIVE",
                settings={"currency": "INR", "price_tolerance_pct": 3.0},
            ),
        ]
        db.add_all(tenants)
        await db.flush()

        # --- Departments (without manager_id first to avoid circular FK) ---
        departments = [
            Department(id=DEPT_ENGINEERING_ID, tenant_id=TENANT_ACME_ID, name="Engineering", code="ENG"),
            Department(id=DEPT_MARKETING_ID, tenant_id=TENANT_ACME_ID, name="Marketing", code="MKT"),
            Department(id=DEPT_OPERATIONS_ID, tenant_id=TENANT_ACME_ID, name="Operations", code="OPS"),
            Department(id=DEPT_FINANCE_ID, tenant_id=TENANT_ACME_ID, name="Finance", code="FIN"),
        ]
        db.add_all(departments)
        await db.flush()

        # --- Users ---
        users = [
            User(id=USER_ADMIN_ID, tenant_id=TENANT_ACME_ID, email="admin@acme.com",
                 password_hash=hashed_pw, first_name="System", last_name="Admin", role="admin"),
            User(id=USER_ENG_MGR_ID, tenant_id=TENANT_ACME_ID, email="eng.manager@acme.com",
                 password_hash=hashed_pw, first_name="Alice", last_name="Johnson",
                 role="manager", department_id=DEPT_ENGINEERING_ID),
            User(id=USER_FINANCE_ID, tenant_id=TENANT_ACME_ID, email="finance@acme.com",
                 password_hash=hashed_pw, first_name="Bob", last_name="Williams",
                 role="finance", department_id=DEPT_FINANCE_ID),
            User(id=USER_FINANCE_HEAD_ID, tenant_id=TENANT_ACME_ID, email="finance.head@acme.com",
                 password_hash=hashed_pw, first_name="Carol", last_name="Davis",
                 role="finance_head", department_id=DEPT_FINANCE_ID),
            User(id=USER_CFO_ID, tenant_id=TENANT_ACME_ID, email="cfo@acme.com",
                 password_hash=hashed_pw, first_name="David", last_name="Wilson",
                 role="cfo", department_id=DEPT_FINANCE_ID),
            User(id=USER_PROCUREMENT_ID, tenant_id=TENANT_ACME_ID, email="procurement@acme.com",
                 password_hash=hashed_pw, first_name="Eve", last_name="Brown",
                 role="procurement", department_id=DEPT_OPERATIONS_ID),
            User(id=USER_PROC_LEAD_ID, tenant_id=TENANT_ACME_ID, email="proc.lead@acme.com",
                 password_hash=hashed_pw, first_name="Frank", last_name="Miller",
                 role="procurement_lead", department_id=DEPT_OPERATIONS_ID),
            User(id=USER_VENDOR_ID, tenant_id=TENANT_ACME_ID, email="sales@alphasupplies.com",
                 password_hash=hashed_pw, first_name="Grace", last_name="Taylor",
                 role="vendor"),
            User(id=USER_MKT_MGR_ID, tenant_id=TENANT_ACME_ID, email="mkt.manager@acme.com",
                 password_hash=hashed_pw, first_name="Henry", last_name="Anderson",
                 role="manager", department_id=DEPT_MARKETING_ID),
            User(id=USER_OPS_MGR_ID, tenant_id=TENANT_ACME_ID, email="ops.manager@acme.com",
                 password_hash=hashed_pw, first_name="Iris", last_name="Thomas",
                 role="manager", department_id=DEPT_OPERATIONS_ID),
        ]
        db.add_all(users)
        await db.flush()

        # --- Update department managers now that users exist ---
        for dept_id, mgr_id in [
            (DEPT_ENGINEERING_ID, USER_ENG_MGR_ID),
            (DEPT_MARKETING_ID, USER_MKT_MGR_ID),
            (DEPT_OPERATIONS_ID, USER_OPS_MGR_ID),
            (DEPT_FINANCE_ID, USER_FINANCE_HEAD_ID),
        ]:
            await db.execute(
                text("UPDATE departments SET manager_id = :mid WHERE id = :did"),
                {"mid": str(mgr_id), "did": str(dept_id)},
            )

        # --- Budgets (Q1 2026) ---
        budgets = [
            Budget(id=BUDGET_ENG_ID, tenant_id=TENANT_ACME_ID, department_id=DEPT_ENGINEERING_ID,
                   fiscal_year=2026, quarter=1, total_cents=50_000_00, spent_cents=12_500_00, currency="INR"),
            Budget(id=BUDGET_MKT_ID, tenant_id=TENANT_ACME_ID, department_id=DEPT_MARKETING_ID,
                   fiscal_year=2026, quarter=1, total_cents=30_000_00, spent_cents=5_000_00, currency="INR"),
            Budget(id=BUDGET_OPS_ID, tenant_id=TENANT_ACME_ID, department_id=DEPT_OPERATIONS_ID,
                   fiscal_year=2026, quarter=1, total_cents=40_000_00, spent_cents=8_000_00, currency="INR"),
            Budget(id=BUDGET_FIN_ID, tenant_id=TENANT_ACME_ID, department_id=DEPT_FINANCE_ID,
                   fiscal_year=2026, quarter=1, total_cents=20_000_00, spent_cents=3_000_00, currency="INR"),
        ]
        db.add_all(budgets)
        await db.flush()

        # --- Vendors ---
        vendors = [
            Vendor(id=VENDOR_ALPHA_ID, tenant_id=TENANT_ACME_ID, legal_name="Alpha Supplies Inc.",
                   tax_id="GSTIN1234500001", email="sales@alphasupplies.com", status="ACTIVE",
                   risk_score=25, rating=8.5),
            Vendor(id=VENDOR_BETA_ID, tenant_id=TENANT_ACME_ID, legal_name="Beta Hardware Ltd.",
                   tax_id="GSTIN1234500002", email="contact@betahw.com", status="ACTIVE",
                   risk_score=40, rating=7.2),
            Vendor(id=VENDOR_GAMMA_ID, tenant_id=TENANT_ACME_ID, legal_name="Gamma Services Co.",
                   tax_id="GSTIN1234500003", email="info@gammaservices.com", status="PENDING_REVIEW",
                   risk_score=60),
            Vendor(id=VENDOR_DELTA_ID, tenant_id=TENANT_ACME_ID, legal_name="Delta Electronics",
                   tax_id="GSTIN1234500004", email="sales@deltaelec.com", status="BLOCKED",
                   risk_score=75, rating=5.0),
            Vendor(id=VENDOR_OMEGA_ID, tenant_id=TENANT_ACME_ID, legal_name="Omega Consulting",
                   tax_id="GSTIN1234500005", email="hello@omegaconsult.com", status="DRAFT"),
        ]
        db.add_all(vendors)

        await db.commit()
        print("Seed data inserted successfully!")
        print(f"  Tenants: 2")
        print(f"  Departments: 4")
        print(f"  Users: 10 (password: {DEFAULT_PASSWORD})")
        print(f"  Budgets: 4")
        print(f"  Vendors: 5")


if __name__ == "__main__":
    asyncio.run(seed())
