"""enable_rls_policies

Revision ID: d2adffc3ac4a
Revises: b064a15c0f06
Create Date: 2026-02-17 01:59:16.679442+00:00

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd2adffc3ac4a'
down_revision: Union[str, None] = 'b064a15c0f06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables with tenant_id that get RLS
RLS_TABLES = [
    "users", "departments", "budgets", "budget_reservations",
    "vendors", "vendor_documents", "purchase_requests", "purchase_orders",
    "invoices", "receipts", "rfqs", "rfq_bids",
    "approvals", "audit_logs", "payments", "user_devices",
]


def upgrade() -> None:
    # Enable RLS and create tenant isolation policies
    for table in RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING (tenant_id = current_setting('app.current_tenant_id')::uuid)"
        )

    # Performance indexes from spec §1.3
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_pr_tenant_status_date "
        "ON purchase_requests(tenant_id, status, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_pr_dept_status "
        "ON purchase_requests(department_id, status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_invoices_vendor_status "
        "ON invoices(vendor_id, status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_invoices_match_status "
        "ON invoices(match_status, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_po_status_delivery "
        "ON purchase_orders(status, expected_delivery_date)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_approvals_user_status "
        "ON approvals(approver_id, status, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_budgets_dept_year_quarter "
        "ON budgets(department_id, fiscal_year, quarter)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_budget_reservations_budget_status "
        "ON budget_reservations(budget_id, status)"
    )
    # pg_trgm GIN index for fuzzy vendor search
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_vendors_name_trgm "
        "ON vendors USING gin (legal_name gin_trgm_ops)"
    )
    # Partial index for active users
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_users_email_active "
        "ON users(email, is_active) WHERE deleted_at IS NULL"
    )


def downgrade() -> None:
    # Drop performance indexes
    op.execute("DROP INDEX IF EXISTS idx_users_email_active")
    op.execute("DROP INDEX IF EXISTS idx_vendors_name_trgm")
    op.execute("DROP INDEX IF EXISTS idx_budget_reservations_budget_status")
    op.execute("DROP INDEX IF EXISTS idx_budgets_dept_year_quarter")
    op.execute("DROP INDEX IF EXISTS idx_approvals_user_status")
    op.execute("DROP INDEX IF EXISTS idx_po_status_delivery")
    op.execute("DROP INDEX IF EXISTS idx_invoices_match_status")
    op.execute("DROP INDEX IF EXISTS idx_invoices_vendor_status")
    op.execute("DROP INDEX IF EXISTS idx_pr_dept_status")
    op.execute("DROP INDEX IF EXISTS idx_pr_tenant_status_date")

    # Drop RLS policies and disable RLS
    for table in reversed(RLS_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
