"""add fx_rates table for multi-currency support

Revision ID: a1b2c3d4e5f6
Revises: c9e1f2a3b4d5
Create Date: 2026-02-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a1b2c3d4e5f6"
down_revision = "c9e1f2a3b4d5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fx_rates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_currency", sa.String(3), nullable=False),
        sa.Column("to_currency", sa.String(3), nullable=False),
        sa.Column("rate", sa.Numeric(20, 6), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "from_currency", "to_currency", "effective_date",
            name="uq_fx_rate_tenant_pair_date",
        ),
    )
    op.create_index("idx_fx_rates_tenant", "fx_rates", ["tenant_id"])
    op.create_index("idx_fx_rates_date", "fx_rates", ["effective_date"])

    # Enable RLS on fx_rates (same pattern as other tables)
    op.execute("ALTER TABLE fx_rates ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation_fx_rates ON fx_rates
            USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_fx_rates ON fx_rates")
    op.drop_index("idx_fx_rates_date", table_name="fx_rates")
    op.drop_index("idx_fx_rates_tenant", table_name="fx_rates")
    op.drop_table("fx_rates")
