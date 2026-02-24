"""merge_heads_for_department_name_constraint

Revision ID: 28f19ed1d2d4
Revises: 41cdfa8bf366, b2c3d4e5f6a7
Create Date: 2026-02-24 09:07:57.307362+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28f19ed1d2d4'
down_revision: Union[str, None] = ('41cdfa8bf366', 'b2c3d4e5f6a7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
