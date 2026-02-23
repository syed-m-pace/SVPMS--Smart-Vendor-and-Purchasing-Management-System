"""add_invoice_payment_fields

Revision ID: 7bcdb952bddf
Revises: f7c2a39d1b8e
Create Date: 2026-02-23 14:12:06.297104+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7bcdb952bddf'
down_revision: Union[str, None] = 'f7c2a39d1b8e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("approved_payment_at", sa.DateTime(), nullable=True))
    op.add_column("invoices", sa.Column("paid_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("invoices", "paid_at")
    op.drop_column("invoices", "approved_payment_at")
