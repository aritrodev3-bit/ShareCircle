import pytest
from pydantic import ValidationError


def test_settings_validation_reports_missing_required_env_vars(monkeypatch):
    from app.config import REQUIRED_ENV_VARS, Settings

    for name in REQUIRED_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    error_text = str(exc_info.value)
    for name in REQUIRED_ENV_VARS:
        assert name.lower() in error_text.lower()


def test_settings_loads_required_values_from_environment(monkeypatch):
    from app.config import Settings

    values = {
        "DATABASE_URL": "postgresql+asyncpg://user:pass@example.com:5432/postgres",
        "ALEMBIC_DATABASE_URL": "postgresql+asyncpg://user:pass@example.com:5432/postgres",
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_ANON_KEY": "anon-key",
        "SUPABASE_JWT_SECRET": "jwt-secret",
        "CELERY_BROKER_URL": "redis://redis:6379/0",
        "CELERY_RESULT_BACKEND": "redis://redis:6379/0",
        "JWT_SECRET_KEY": "a" * 32,
        "RESEND_API_KEY": "re_test",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)

    settings = Settings(_env_file=None)

    assert str(settings.database_url).startswith("postgresql+asyncpg://")
    assert settings.jwt_algorithm == "HS256"
    assert settings.access_token_expire_minutes == 60
    assert settings.resend_from_email == "onboarding@resend.dev"
