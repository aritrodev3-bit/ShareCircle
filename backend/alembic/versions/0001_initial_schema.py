"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-03 00:00:00.000000
"""

from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_role = postgresql.ENUM("donor", "recipient", "ngo", "admin", name="user_role", create_type=False)
item_category = postgresql.ENUM(
    "clothing",
    "furniture",
    "electronics",
    "books",
    "kitchen",
    "toys",
    "medical",
    "other",
    name="item_category",
    create_type=False,
)
item_condition = postgresql.ENUM(
    "new",
    "like_new",
    "good",
    "fair",
    name="item_condition",
    create_type=False,
)
item_status = postgresql.ENUM(
    "available",
    "reserved",
    "donated",
    "removed",
    name="item_status",
    create_type=False,
)
request_status = postgresql.ENUM(
    "pending",
    "approved",
    "rejected",
    "picked_up",
    "cancelled",
    name="request_status",
    create_type=False,
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE user_role AS ENUM ('donor', 'recipient', 'ngo', 'admin');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END
        $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE item_category AS ENUM (
                'clothing',
                'furniture',
                'electronics',
                'books',
                'kitchen',
                'toys',
                'medical',
                'other'
            );
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END
        $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE item_condition AS ENUM ('new', 'like_new', 'good', 'fair');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END
        $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE item_status AS ENUM ('available', 'reserved', 'donated', 'removed');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END
        $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE request_status AS ENUM (
                'pending',
                'approved',
                'rejected',
                'picked_up',
                'cancelled'
            );
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END
        $$;
        """
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column(
            "preferred_categories",
            postgresql.ARRAY(sa.String()),
            server_default=sa.text("'{}'::varchar[]"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)

    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("donor_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", item_category, nullable=False),
        sa.Column("condition", item_condition, nullable=False),
        sa.Column("quantity", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("status", item_status, server_default="available", nullable=False),
        sa.Column(
            "location",
            geoalchemy2.Geography(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=True,
        ),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("pincode", sa.String(length=10), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("donated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["donor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_items_category", "items", ["category"], unique=False)
    op.create_index("ix_items_city", "items", ["city"], unique=False)
    op.create_index("ix_items_donor_id", "items", ["donor_id"], unique=False)
    op.create_index("ix_items_location", "items", ["location"], unique=False, postgresql_using="gist")
    op.create_index("ix_items_status", "items", ["status"], unique=False)

    op.create_table(
        "donation_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("requester_id", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("ngo_note", sa.Text(), nullable=True),
        sa.Column("status", request_status, server_default="pending", nullable=False),
        sa.Column("pickup_scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("picked_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_donation_requests_item_id", "donation_requests", ["item_id"], unique=False)
    op.create_index(
        "ix_donation_requests_requester_id",
        "donation_requests",
        ["requester_id"],
        unique=False,
    )
    op.create_index("ix_donation_requests_status", "donation_requests", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_donation_requests_status", table_name="donation_requests")
    op.drop_index("ix_donation_requests_requester_id", table_name="donation_requests")
    op.drop_index("ix_donation_requests_item_id", table_name="donation_requests")
    op.drop_table("donation_requests")

    op.drop_index("ix_items_status", table_name="items")
    op.drop_index("ix_items_location", table_name="items")
    op.drop_index("ix_items_donor_id", table_name="items")
    op.drop_index("ix_items_city", table_name="items")
    op.drop_index("ix_items_category", table_name="items")
    op.drop_table("items")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS request_status")
    op.execute("DROP TYPE IF EXISTS item_status")
    op.execute("DROP TYPE IF EXISTS item_condition")
    op.execute("DROP TYPE IF EXISTS item_category")
    op.execute("DROP TYPE IF EXISTS user_role")
