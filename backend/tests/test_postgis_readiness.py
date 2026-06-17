import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings


@pytest.mark.asyncio
async def test_postgis_extension_is_enabled():
    settings = get_settings()
    engine = create_async_engine(
        str(settings.database_url),
        pool_pre_ping=True,
        connect_args={"statement_cache_size": 0},
    )

    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("select postgis_version()"))
    finally:
        await engine.dispose()

    assert result.scalar_one()
