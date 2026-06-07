import pytest
from sqlalchemy import text

from app.database import async_session_factory
from app.models import Base


@pytest.mark.asyncio
async def test_postgis_extension_and_geography_column_exist():
    async with async_session_factory() as session:
        postgis_version = await session.execute(text("select postgis_version()"))
        geography_type = await session.execute(
            text(
                """
                select format_type(attribute.atttypid, attribute.atttypmod)
                from pg_attribute attribute
                join pg_class class on class.oid = attribute.attrelid
                join pg_namespace namespace on namespace.oid = class.relnamespace
                where namespace.nspname = 'public'
                  and class.relname = 'items'
                  and attribute.attname = 'location'
                  and not attribute.attisdropped
                """
            )
        )

    assert postgis_version.scalar_one()
    assert geography_type.scalar_one() == "geography(Point,4326)"


@pytest.mark.asyncio
async def test_required_tables_and_indexes_exist():
    expected_tables = {"users", "items", "donation_requests"}
    expected_indexes = {
        "ix_users_email",
        "ix_users_supabase_user_id",
        "ix_items_status",
        "ix_items_category",
        "ix_items_city",
        "ix_items_donor_id",
        "ix_items_location",
        "ix_donation_requests_item_id",
        "ix_donation_requests_requester_id",
        "ix_donation_requests_status",
    }

    async with async_session_factory() as session:
        table_rows = await session.execute(
            text(
                """
                select table_name
                from information_schema.tables
                where table_schema = 'public'
                  and table_name = any(:table_names)
                """
            ),
            {"table_names": list(expected_tables)},
        )
        index_rows = await session.execute(
            text(
                """
                select indexname
                from pg_indexes
                where schemaname = 'public'
                  and indexname = any(:index_names)
                """
            ),
            {"index_names": list(expected_indexes)},
        )
        spatial_index = await session.execute(
            text(
                """
                select indexdef
                from pg_indexes
                where schemaname = 'public'
                  and tablename = 'items'
                  and indexname = 'ix_items_location'
                """
            )
        )

    assert {row[0] for row in table_rows} == expected_tables
    assert {row[0] for row in index_rows} == expected_indexes
    assert "gist" in spatial_index.scalar_one().lower()


def test_metadata_imports_all_phase_2_models_and_defers_notifications():
    assert set(Base.metadata.tables.keys()) == {"users", "items", "donation_requests"}
