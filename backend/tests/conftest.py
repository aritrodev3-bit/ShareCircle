import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Force database URL to test database for all test executions
load_dotenv(BACKEND_ROOT / ".env")
load_dotenv(BACKEND_ROOT.parent / ".env")
test_db_url = os.getenv("TEST_DATABASE_URL")
if test_db_url:
    os.environ["DATABASE_URL"] = test_db_url
    os.environ["ALEMBIC_DATABASE_URL"] = test_db_url

@pytest.fixture(autouse=True, scope="session")
def configure_celery_eager():
    """GAP-7: Import Celery inside the fixture so it runs after all conftest
    module-level setup (including DATABASE_URL override) has completed."""
    from app.worker.celery_app import celery_app
    celery_app.conf.task_always_eager = True


@pytest.fixture
def client():
    from app.main import create_app

    return TestClient(create_app())

