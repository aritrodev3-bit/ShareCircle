"""make role nullable

Revision ID: 0003_make_role_nullable
Revises: 0002_add_supabase_user_id
Create Date: 2026-06-16 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_make_role_nullable"
down_revision: Union[str, None] = "0002_add_supabase_user_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "role",
        existing_type=sa.Enum("donor", "recipient", "ngo", "admin", name="user_role"),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "role",
        existing_type=sa.Enum("donor", "recipient", "ngo", "admin", name="user_role"),
        nullable=False,
    )
