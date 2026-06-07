"""add supabase user id

Revision ID: 0002_add_supabase_user_id
Revises: 0001_initial_schema
Create Date: 2026-06-07 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_add_supabase_user_id"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("supabase_user_id", sa.String(length=36), nullable=True))
    op.create_index("ix_users_supabase_user_id", "users", ["supabase_user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_supabase_user_id", table_name="users")
    op.drop_column("users", "supabase_user_id")
