"""
Global pytest configuration for SIH APAAR Platform.
Enforces strict test isolation:
- All database operations are redirected to an isolated temporary SQLite database.
- All file uploads are redirected to an isolated temporary directory.
- The development database ('apaar_platform.db') and repository upload storage ('./uploaded_datasets')
  are completely protected and cannot be written to, reset, or modified by tests.
- On test session completion, all temporary artifacts are cleaned up safely.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# 1. Create temporary directory for test database and uploads before importing app modules
_TEST_TEMP_DIR = tempfile.mkdtemp(prefix="sih_apaar_test_")
_TEST_DB_PATH = os.path.join(_TEST_TEMP_DIR, "isolated_test.db")
_TEST_DB_URL = f"sqlite:///{_TEST_DB_PATH}"
_TEST_UPLOAD_DIR = os.path.join(_TEST_TEMP_DIR, "test_uploads")
os.makedirs(_TEST_UPLOAD_DIR, exist_ok=True)

# Set environment variables so any early config reads use the test environment
os.environ["DATABASE_URL"] = _TEST_DB_URL
os.environ["UPLOAD_STORAGE_DIR"] = _TEST_UPLOAD_DIR
os.environ["ENVIRONMENT"] = "test"
os.environ["ALLOW_DEV_DB_RESET"] = "false"

# Import settings and db modules now that env is primed
from backend.app.core.config import settings
from backend.app.db import session as db_session
from backend.app.seed.seed_data import seed_database
from backend.app import main as app_main

# Re-point settings attributes to guarantee consistency even if config was loaded
settings.DATABASE_URL = _TEST_DB_URL
settings.UPLOAD_STORAGE_DIR = _TEST_UPLOAD_DIR
settings.ENVIRONMENT = "test"

# Reconfigure SQLAlchemy engine & SessionLocal to bind strictly to the test database
_test_engine = create_engine(
    _TEST_DB_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
    echo=False
)

@event.listens_for(_test_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()

_TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)

# Monkeypatch db_session module attributes
db_session.engine = _test_engine
db_session.SessionLocal = _TestSessionLocal

# Also ensure seed_data references the test engine and sessionmaker
from backend.app.seed import seed_data
seed_data.engine = _test_engine
seed_data.SessionLocal = _TestSessionLocal

# Initialize schema and seed synthetic data in the test database
db_session.init_db()
seed_database(reset=False)


@pytest.fixture(scope="session", autouse=True)
def enforce_test_isolation():
    """
    Session-wide fixture ensuring no test touches the real development database
    or the repository's uploaded_datasets directory.
    """
    # Guard assertion: fail fast if somehow pointing to development database
    assert "apaar_platform.db" not in settings.DATABASE_URL or "test_apaar_platform.db" in settings.DATABASE_URL, (
        f"CRITICAL TEST ISOLATION FAILURE: settings.DATABASE_URL is pointing to {settings.DATABASE_URL}"
    )
    assert not os.path.abspath(settings.UPLOAD_STORAGE_DIR).endswith("uploaded_datasets") or "sih_apaar_test_" in settings.UPLOAD_STORAGE_DIR, (
        f"CRITICAL TEST ISOLATION FAILURE: settings.UPLOAD_STORAGE_DIR is pointing to {settings.UPLOAD_STORAGE_DIR}"
    )

    yield {
        "temp_dir": _TEST_TEMP_DIR,
        "db_url": _TEST_DB_URL,
        "upload_dir": _TEST_UPLOAD_DIR,
    }

    # Teardown: close engine connections and remove temporary directory
    _test_engine.dispose()
    shutil.rmtree(_TEST_TEMP_DIR, ignore_errors=True)
