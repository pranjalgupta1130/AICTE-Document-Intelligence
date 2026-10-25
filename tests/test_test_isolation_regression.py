"""
Regression tests for test isolation and safe file handling.

Verifies:
1. Test uploads are written to isolated temporary storage and never to the repository uploaded_datasets directory.
2. Database writes by tests are committed strictly to the test database and cannot affect apaar_platform.db.
3. Attempting a destructive reset on apaar_platform.db fails safe with RuntimeError.
4. Missing original upload files produce clean HTTP 404 errors without crashing the application.
"""

import os
import sqlite3
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.db.session import SessionLocal
from backend.app.models.batch import ImportBatch
from backend.app.models.enums import BatchStatus
from backend.app.seed.seed_data import seed_database


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def get_auth_token(client: TestClient, email: str = "apex_operator@apex.edu.in", password: str = "DemoPassword@2026") -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


def test_uploads_written_to_isolated_temp_storage(client: TestClient):
    """Confirm uploads are written strictly to isolated temporary storage, never repo upload dir."""
    token = get_auth_token(client)
    csv_payload = (
        "institution_student_id,student_name,programme_id,academic_year\n"
        "ISOL-TEST-001,Isolation Student,PROG-001-CSE,2026-2027\n"
    )
    files = {"file": ("isolation_test.csv", csv_payload, "text/csv")}
    res = client.post(
        "/api/v1/imports",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data={"academic_year": "2026-2027"}
    )
    assert res.status_code == 200, f"Upload failed: {res.text}"
    data = res.json()
    batch_id = data["batch_id"]

    # Verify batch storage_path in test database
    db = SessionLocal()
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    assert batch is not None
    assert batch.storage_path is not None
    stored_filename = os.path.basename(batch.storage_path)
    db.close()

    # The file MUST exist in settings.UPLOAD_STORAGE_DIR (temporary directory)
    temp_file_path = os.path.join(settings.UPLOAD_STORAGE_DIR, stored_filename)
    assert os.path.exists(temp_file_path), f"Expected file in temp storage: {temp_file_path}"
    assert "sih_apaar_test_" in settings.UPLOAD_STORAGE_DIR

    # The file MUST NOT exist in the repository's uploaded_datasets directory
    repo_file_path = os.path.join("./uploaded_datasets", stored_filename)
    assert not os.path.exists(repo_file_path), f"File leaked into repository uploaded_datasets: {repo_file_path}"


def test_test_database_writes_do_not_affect_dev_database(client: TestClient):
    """Confirm that database writes by tests do not touch apaar_platform.db."""
    # 1. Read row count from apaar_platform.db before test action
    dev_db_path = os.path.abspath("apaar_platform.db")
    assert os.path.exists(dev_db_path), "apaar_platform.db must exist for validation"

    conn = sqlite3.connect(dev_db_path)
    c = conn.cursor()
    c.execute("SELECT count(*) FROM import_batches")
    dev_batches_before = c.fetchone()[0]
    conn.close()

    # 2. Insert a test record through test SessionLocal
    test_batch_id = f"BATCH-ISOL-{uuid.uuid4().hex[:8]}"
    db = SessionLocal()
    test_batch = ImportBatch(
        id=test_batch_id,
        institution_id="INST-001",
        academic_year="2026-2027",
        source_filename="isolation_db_test.csv",
        version=9999,
        status=BatchStatus.DRAFT
    )
    db.add(test_batch)
    db.commit()

    # Verify present in test database
    in_test_db = db.query(ImportBatch).filter(ImportBatch.id == test_batch_id).first()
    assert in_test_db is not None
    db.close()

    # 3. Read row count from apaar_platform.db after test action
    conn = sqlite3.connect(dev_db_path)
    c = conn.cursor()
    c.execute("SELECT count(*) FROM import_batches")
    dev_batches_after = c.fetchone()[0]
    c.execute("SELECT count(*) FROM import_batches WHERE id = ?", (test_batch_id,))
    dev_contains_test_batch = c.fetchone()[0]
    conn.close()

    # Must be completely unchanged in dev database
    assert dev_batches_after == dev_batches_before, "Dev database batch count was altered by test!"
    assert dev_contains_test_batch == 0, "Test batch leaked into apaar_platform.db!"


def test_seed_database_fails_safe_on_dev_database():
    """Verify that seed_database(reset=True) refuses to drop tables if pointed at apaar_platform.db."""
    from backend.app.seed import seed_data
    from backend.app.db import session as db_session
    from sqlalchemy import create_engine

    dev_engine = create_engine("sqlite:///./apaar_platform.db")
    original_engine = getattr(db_session, "engine", None)

    try:
        db_session.engine = dev_engine
        # Without ALLOW_DEV_DB_RESET=true, this MUST raise RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
            seed_database(reset=True)
        assert "Destructive reset blocked" in str(exc_info.value)
    finally:
        db_session.engine = original_engine
        dev_engine.dispose()


def test_missing_original_upload_file_returns_clean_404(client: TestClient):
    """Verify that attempting to download a batch whose upload file is missing returns a clean 404."""
    token = get_auth_token(client, email="apex_admin@apex.edu.in")

    # Create a batch in test DB with a nonexistent storage_path
    batch_id = f"BATCH-MISSING-{uuid.uuid4().hex[:6]}"
    db = SessionLocal()
    batch = ImportBatch(
        id=batch_id,
        institution_id="INST-001",
        academic_year="2026-2027",
        source_filename="missing_test.csv",
        storage_path="nonexistent_storage_file_xyz.dat",
        version=8888,
        status=BatchStatus.DRAFT
    )
    db.add(batch)
    db.commit()
    db.close()

    resp = client.get(
        f"/api/v1/batches/{batch_id}/download",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 404
    error_message = resp.json()["error"]["message"]
    assert "Original file unavailable" in error_message
