"""add_po_issued_at_and_user_profile_photo

Revision ID: e3a4b44a9c12
Revises: d2adffc3ac4a
Create Date: 2026-02-19 18:20:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e3a4b44a9c12"
down_revision: Union[str, None] = "d2adffc3ac4a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("purchase_orders", sa.Column("issued_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("profile_photo_url", sa.Text(), nullable=True))

    # Backfill issued_at for existing POs that have already been issued/processed.
    op.execute(
        """
        UPDATE purchase_orders
        SET issued_at = COALESCE(issued_at, created_at)
        WHERE status IN ('ISSUED', 'ACKNOWLEDGED', 'PARTIALLY_FULFILLED', 'FULFILLED', 'CLOSED')
        """
    )


def downgrade() -> None:
    op.drop_column("users", "profile_photo_url")
    op.drop_column("purchase_orders", "issued_at")
