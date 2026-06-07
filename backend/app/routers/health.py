from fastapi import APIRouter, HTTPException
from redis.asyncio import Redis
from sqlalchemy import text

from app.config import get_settings
from app.database import engine

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "api"}


@router.get("/health/db")
async def db_health():
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            result.scalar_one()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc

    return {"status": "ok", "service": "db"}


@router.get("/health/redis")
async def redis_health():
    settings = get_settings()
    redis = Redis.from_url(str(settings.celery_broker_url), decode_responses=True)
    try:
        pong = await redis.ping()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="redis unavailable") from exc
    finally:
        await redis.aclose()

    if pong is not True:
        raise HTTPException(status_code=503, detail="redis unavailable")

    return {"status": "ok", "service": "redis"}
