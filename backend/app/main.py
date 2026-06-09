from fastapi import FastAPI

from app.routers import analytics, auth, health, items, matching, requests


def create_app() -> FastAPI:
    app = FastAPI(title="GiveCircle API")
    app.include_router(auth.router)
    app.include_router(items.router)
    app.include_router(requests.router)
    app.include_router(matching.router)
    app.include_router(analytics.router)
    app.include_router(health.router)
    return app


app = create_app()
