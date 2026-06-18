from functools import lru_cache
from typing import Annotated

from pydantic import AnyUrl, Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

REQUIRED_ENV_VARS = (
    "DATABASE_URL",
    "ALEMBIC_DATABASE_URL",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_JWT_SECRET",
    "CELERY_BROKER_URL",
    "CELERY_RESULT_BACKEND",
    "JWT_SECRET_KEY",
    "RESEND_API_KEY",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
        case_sensitive=False,
    )

    supabase_project_ref: str | None = None
    supabase_db_password: str | None = None
    database_url: Annotated[PostgresDsn, Field(alias="DATABASE_URL")]
    alembic_database_url: Annotated[PostgresDsn, Field(alias="ALEMBIC_DATABASE_URL")]
    test_database_url: PostgresDsn | None = None

    supabase_url: Annotated[AnyUrl, Field(alias="SUPABASE_URL")]
    supabase_anon_key: Annotated[str, Field(alias="SUPABASE_ANON_KEY")]
    supabase_jwt_secret: Annotated[str, Field(alias="SUPABASE_JWT_SECRET")]

    celery_broker_url: Annotated[RedisDsn, Field(alias="CELERY_BROKER_URL")]
    celery_result_backend: Annotated[RedisDsn, Field(alias="CELERY_RESULT_BACKEND")]
    celery_task_max_retries: int = 3

    jwt_secret_key: Annotated[str, Field(alias="JWT_SECRET_KEY", min_length=32)]
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    resend_api_key: Annotated[str, Field(alias="RESEND_API_KEY")]
    resend_from_email: str = "onboarding@resend.dev"

    api_base_url: AnyUrl = "http://localhost:8000"
    public_app_url: AnyUrl = "http://localhost:8501"
    api_public_url: AnyUrl = "http://localhost:8000"
    cors_allowed_origins: str = "http://localhost:8501,http://localhost:3000"
    google_redirect_uri: AnyUrl = "http://localhost:8000/api/auth/callback/google"
    frontend_oauth_redirect_url: AnyUrl = "http://localhost:3000/auth/callback"

    environment: str = "local"
    log_level: str = "INFO"
    sentry_dsn: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
