from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.config import get_settings
from app.routers import analytics, auth, health, items, matching, requests


def create_app() -> FastAPI:
    app = FastAPI(title="GiveCircle API")
    
    # Configure CORS
    settings = get_settings()
    origins = [origin.strip() for origin in settings.cors_allowed_origins.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Ensure static directory exists
    os.makedirs("app/static/uploads", exist_ok=True)
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    app.include_router(auth.router)
    app.include_router(items.router)
    app.include_router(requests.router)
    app.include_router(matching.router)
    app.include_router(analytics.router)
    app.include_router(health.router)
    return app


app = create_app()
