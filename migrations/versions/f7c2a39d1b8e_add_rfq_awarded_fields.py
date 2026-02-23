"""add_rfq_awarded_fields

Revision ID: f7c2a39d1b8e
Revises: e3a4b44a9c12
Create Date: 2026-02-23 10:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID


# revision identifiers, used by Alembic.
revision: str = "f7c2a39d1b8e"
down_revision: Union[str, None] = "e3a4b44a9c12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("rfqs", sa.Column("awarded_vendor_id", PGUUID(), nullable=True))
    op.add_column("rfqs", sa.Column("awarded_po_id", PGUUID(), nullable=True))
    op.create_foreign_key(
        "fk_rfq_awarded_vendor", "rfqs", "vendors", ["awarded_vendor_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_rfq_awarded_po", "rfqs", "purchase_orders", ["awarded_po_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_rfq_awarded_po", "rfqs", type_="foreignkey")
    op.drop_constraint("fk_rfq_awarded_vendor", "rfqs", type_="foreignkey")
    op.drop_column("rfqs", "awarded_po_id")
    op.drop_column("rfqs", "awarded_vendor_id")
