"""add_missing_indexes

Revision ID: c9e1f2a3b4d5
Revises: 7bcdb952bddf
Create Date: 2026-02-23 15:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9e1f2a3b4d5'
down_revision: Union[str, None] = '7bcdb952bddf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("idx_rfq_line_items_rfq", "rfq_line_items", ["rfq_id"])
    op.create_index("idx_receipt_line_items_receipt", "receipt_line_items", ["receipt_id"])
    op.create_index("idx_rfqs_tenant", "rfqs", ["tenant_id"])
    op.create_index("idx_rfqs_status", "rfqs", ["status"])


def downgrade() -> None:
    op.drop_index("idx_rfqs_status", table_name="rfqs")
    op.drop_index("idx_rfqs_tenant", table_name="rfqs")
    op.drop_index("idx_receipt_line_items_receipt", table_name="receipt_line_items")
    op.drop_index("idx_rfq_line_items_rfq", table_name="rfq_line_items")
