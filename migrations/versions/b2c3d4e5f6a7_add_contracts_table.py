"""add contracts table for contract management module

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-24 00:00:01.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contracts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contract_number", sa.String(50), unique=True, nullable=False),
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("po_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="DRAFT"),
        sa.Column("value_cents", sa.BigInteger(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("auto_renew", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("renewal_notice_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("document_key", sa.String(255), nullable=True),
        sa.Column("sla_terms", sa.Text(), nullable=True),
        sa.Column("terminated_at", sa.DateTime(), nullable=True),
        sa.Column("termination_reason", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.id"]),
        sa.ForeignKeyConstraint(["po_id"], ["purchase_orders.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('DRAFT','ACTIVE','EXPIRED','TERMINATED')",
            name="chk_contract_status",
        ),
    )
    op.create_index("idx_contracts_tenant", "contracts", ["tenant_id"])
    op.create_index("idx_contracts_vendor", "contracts", ["vendor_id"])
    op.create_index("idx_contracts_status", "contracts", ["status"])
    op.create_index("idx_contracts_end_date", "contracts", ["end_date"])

    # Enable RLS
    op.execute("ALTER TABLE contracts ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_contracts ON contracts
            USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_contracts ON contracts")
    op.drop_index("idx_contracts_end_date", table_name="contracts")
    op.drop_index("idx_contracts_status", table_name="contracts")
    op.drop_index("idx_contracts_vendor", table_name="contracts")
    op.drop_index("idx_contracts_tenant", table_name="contracts")
    op.drop_table("contracts")
