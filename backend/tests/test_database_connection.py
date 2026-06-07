import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_database_engine_executes_select_one():
    from app.database import engine

    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
    finally:
        await engine.dispose()

    assert result.scalar_one() == 1
