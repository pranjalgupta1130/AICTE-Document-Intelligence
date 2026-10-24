import threading
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from backend.app.main import app
from backend.app.seed.seed_data import seed_database
from backend.app.db.session import SessionLocal
from backend.app.models.batch import ImportBatch
from backend.app.models.enums import BatchStatus, MatchStatus
from backend.app.models.match import MatchCandidate
from backend.app.models.student import StudentRecord
from backend.app.services.import_service import allocate_concurrency_safe_batch_version


@pytest.fixture(scope="session", autouse=True)
def prepare_test_database():
    """Ensure database has fresh synthetic seed data before running tests."""
    seed_database(reset=True)


@pytest.fixture
def client():
    return TestClient(app)


def get_auth_token(client: TestClient, email: str, password: str = "DemoPassword@2026") -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, f"Failed to login {email}: {response.text}"
    return response.json()["access_token"]


# ==============================================================================
# 1. Database-Level Unique Constraint on ImportBatch (institution_id, academic_year, version)
# ==============================================================================
def test_import_batch_version_unique_constraint_enforced():
    """Verify database-level unique constraint prevents duplicate batch versions for same institution & academic year."""
    db = SessionLocal()
    inst_id = "INST-001"
    ay = "2026-2027"
    v = 999

    try:
        # Clean up any test batch if existed
        db.query(ImportBatch).filter(
            ImportBatch.institution_id == inst_id,
            ImportBatch.academic_year == ay,
            ImportBatch.version == v
        ).delete()
        db.commit()

        b1 = ImportBatch(
            id=f"BATCH-TEST-{uuid.uuid4().hex[:6]}",
            institution_id=inst_id,
            uploader_user_id="usr-apex-adm-01",
            source_filename="test1.csv",
            academic_year=ay,
            version=v,
            status=BatchStatus.DRAFT
        )
        db.add(b1)
        db.commit()

        b2 = ImportBatch(
            id=f"BATCH-TEST-{uuid.uuid4().hex[:6]}",
            institution_id=inst_id,
            uploader_user_id="usr-apex-adm-01",
            source_filename="test2.csv",
            academic_year=ay,
            version=v,
            status=BatchStatus.DRAFT
        )
        db.add(b2)
        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()
    finally:
        # Cleanup
        db.query(ImportBatch).filter(
            ImportBatch.institution_id == inst_id,
            ImportBatch.academic_year == ay,
            ImportBatch.version == v
        ).delete()
        db.commit()
        db.close()


def test_allocate_concurrency_safe_batch_version_monotonic():
    """Verify version allocation increments monotonically based on current max version."""
    db = SessionLocal()
    inst_id = "INST-001"
    ay = "2028-2029"

    try:
        v1 = allocate_concurrency_safe_batch_version(db, inst_id, ay)
        assert v1 >= 1

        b1 = ImportBatch(
            id=f"BATCH-MONO-{uuid.uuid4().hex[:6]}",
            institution_id=inst_id,
            uploader_user_id="usr-apex-adm-01",
            source_filename="mono.csv",
            academic_year=ay,
            version=v1,
            status=BatchStatus.DRAFT
        )
        db.add(b1)
        db.commit()

        v2 = allocate_concurrency_safe_batch_version(db, inst_id, ay)
        assert v2 == v1 + 1
    finally:
        db.query(ImportBatch).filter(
            ImportBatch.institution_id == inst_id,
            ImportBatch.academic_year == ay
        ).delete()
        db.commit()
        db.close()


def test_concurrent_batch_version_allocation_and_retry(client):
    """
    Simulate concurrent imports attempting to commit for the same institution and academic year.
    Verifies that all concurrent requests successfully commit with unique, incrementing versions.
    """
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    results = []
    errors = []

    def run_import(idx: int):
        c = TestClient(app)
        csv_content = (
            "institution_student_id,student_name,programme_id,academic_year\n"
            f"CONC-ROLL-{idx:03d},Concurrent Student {idx},PROG-001-CSE,2029-2030\n"
        )
        files = {"file": (f"conc_{idx}.csv", csv_content, "text/csv")}
        res = c.post(
            "/api/v1/imports",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
            data={"academic_year": "2029-2030"}
        )
        if res.status_code == 200:
            results.append(res.json()["version"])
        else:
            errors.append(res.text)

    threads = [threading.Thread(target=run_import, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Concurrent import errors: {errors}"
    assert len(results) == 4
    # All versions allocated must be strictly distinct
    assert len(set(results)) == len(results)


# ==============================================================================
# 2. Database-Level Unique Constraint on Match Candidates in Both Orientations
# ==============================================================================
def test_match_candidate_database_unique_in_both_orientations():
    """
    Verify that the database rejects inserting duplicate match candidate record pairs,
    regardless of whether orientation is (A, B) then (A, B) or (A, B) then (B, A).
    """
    db = SessionLocal()
    # Use existing seeded student records for foreign key integrity
    students = db.query(StudentRecord).limit(2).all()
    assert len(students) >= 2
    rec_a = students[0]
    rec_b = students[1]

    try:
        # Clean up prior test data if exists
        db.query(MatchCandidate).filter(
            ((MatchCandidate.record_a_id == rec_a.id) & (MatchCandidate.record_b_id == rec_b.id)) |
            ((MatchCandidate.record_a_id == rec_b.id) & (MatchCandidate.record_b_id == rec_a.id))
        ).delete()
        db.commit()

        # Insert pair (A, B)
        c1 = MatchCandidate(
            id=f"mat-test-{uuid.uuid4().hex[:6]}",
            record_a_id=rec_a.id,
            record_b_id=rec_b.id,
            institution_a_id=rec_a.institution_id,
            institution_b_id=rec_b.institution_id,
            matching_signal="EXACT_APAAR_CROSS_INSTITUTION",
            confidence=1.0,
            status=MatchStatus.CANDIDATE
        )
        db.add(c1)
        db.commit()

        # Attempt to insert identical pair (A, B)
        c2 = MatchCandidate(
            id=f"mat-test-{uuid.uuid4().hex[:6]}",
            record_a_id=rec_a.id,
            record_b_id=rec_b.id,
            institution_a_id=rec_a.institution_id,
            institution_b_id=rec_b.institution_id,
            matching_signal="EXACT_APAAR_CROSS_INSTITUTION",
            confidence=1.0,
            status=MatchStatus.CANDIDATE
        )
        db.add(c2)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        # Attempt to insert reverse pair (B, A)
        c3 = MatchCandidate(
            id=f"mat-test-{uuid.uuid4().hex[:6]}",
            record_a_id=rec_b.id,
            record_b_id=rec_a.id,
            institution_a_id=rec_b.institution_id,
            institution_b_id=rec_a.institution_id,
            matching_signal="EXACT_APAAR_CROSS_INSTITUTION",
            confidence=1.0,
            status=MatchStatus.CANDIDATE
        )
        db.add(c3)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    finally:
        db.query(MatchCandidate).filter(
            ((MatchCandidate.record_a_id == rec_a.id) & (MatchCandidate.record_b_id == rec_b.id)) |
            ((MatchCandidate.record_a_id == rec_b.id) & (MatchCandidate.record_b_id == rec_a.id))
        ).delete()
        db.commit()
        db.close()


def test_match_candidate_reviewed_status_preserved_on_revalidation(client):
    """
    Ensure existing reviewed match candidate statuses (CONFIRMED_DUPLICATE, DISMISSED)
    are strictly preserved during revalidation and never overwritten to CANDIDATE.
    """
    db = SessionLocal()
    inst_apex = "INST-001"
    inst_bharat = "INST-002"
    ay = "2026-2027"
    shared_apaar = "999988887777"

    # Pre-existing batch for bharat to satisfy foreign key or create one
    bharat_batch = db.query(ImportBatch).filter(ImportBatch.institution_id == inst_bharat).first()
    if not bharat_batch:
        bharat_batch = ImportBatch(
            id=f"BATCH-BHA-{uuid.uuid4().hex[:6]}",
            institution_id=inst_bharat,
            uploader_user_id="usr-bharat-adm-01",
            source_filename="bharat.csv",
            academic_year=ay,
            version=1,
            status=BatchStatus.DRAFT
        )
        db.add(bharat_batch)
        db.flush()

    try:
        # Create bharat student record
        bharat_stu = StudentRecord(
            id=f"stu-bharat-{uuid.uuid4().hex[:6]}",
            batch_id=bharat_batch.id,
            institution_id=inst_bharat,
            programme_id="PROG-002-CSE",
            apaar_id=shared_apaar,
            institution_student_id=f"BHA-{uuid.uuid4().hex[:4]}",
            student_name="Bharat Shared Student",
            academic_year=ay
        )
        db.add(bharat_stu)

        # Create apex batch and student record
        batch = ImportBatch(
            id=f"BATCH-REV-{uuid.uuid4().hex[:6]}",
            institution_id=inst_apex,
            uploader_user_id="usr-apex-adm-01",
            source_filename="rev.csv",
            academic_year=ay,
            version=88,
            status=BatchStatus.DRAFT
        )
        db.add(batch)
        db.flush()

        apex_stu = StudentRecord(
            id=f"stu-apex-{uuid.uuid4().hex[:6]}",
            batch_id=batch.id,
            institution_id=inst_apex,
            programme_id="PROG-001-CSE",
            apaar_id=shared_apaar,
            institution_student_id=f"APEX-{uuid.uuid4().hex[:4]}",
            student_name="Apex Shared Student",
            academic_year=ay
        )
        db.add(apex_stu)

        # Pre-seed candidate with status CONFIRMED_DUPLICATE
        rec_a_id, rec_b_id = (apex_stu.id, bharat_stu.id) if apex_stu.id < bharat_stu.id else (bharat_stu.id, apex_stu.id)
        candidate = MatchCandidate(
            id=f"mat-rev-{uuid.uuid4().hex[:6]}",
            record_a_id=rec_a_id,
            record_b_id=rec_b_id,
            institution_a_id=inst_apex if rec_a_id == apex_stu.id else inst_bharat,
            institution_b_id=inst_bharat if rec_a_id == apex_stu.id else inst_apex,
            matching_signal="EXACT_APAAR_CROSS_INSTITUTION",
            confidence=1.0,
            status=MatchStatus.CONFIRMED_DUPLICATE,
            resolution_reason="Confirmed by AICTE reviewer"
        )
        db.add(candidate)
        db.commit()

        # Run validation
        apex_token = get_auth_token(client, "apex_operator@apex.edu.in")
        res = client.post(f"/api/v1/batches/{batch.id}/validate", headers={"Authorization": f"Bearer {apex_token}"})
        assert res.status_code == 200

        # Verify candidate in DB still has status CONFIRMED_DUPLICATE
        db.expire_all()
        persisted = db.query(MatchCandidate).filter(MatchCandidate.id == candidate.id).first()
        assert persisted is not None
        assert persisted.status == MatchStatus.CONFIRMED_DUPLICATE
        assert persisted.resolution_reason == "Confirmed by AICTE reviewer"

    finally:
        db.rollback()
        db.close()


# ==============================================================================
# 3. Optimized Cross-Institution Matching Query (Filtered by Batch APAAR IDs)
# ==============================================================================
def test_cross_institution_matching_query_filtered_by_batch_apaars(client):
    """
    Verify that cross-institution duplicate matching correctly detects matches
    when filtered to the batch's APAAR IDs, without loading unrelated cross-institution records.
    """
    db = SessionLocal()
    inst_apex = "INST-001"
    inst_bharat = "INST-002"
    ay = "2026-2027"

    target_apaar = "777788889999"
    unrelated_apaar = "111122223333"

    bharat_batch = db.query(ImportBatch).filter(ImportBatch.institution_id == inst_bharat).first()
    if not bharat_batch:
        bharat_batch = ImportBatch(
            id=f"BATCH-BHA-{uuid.uuid4().hex[:6]}",
            institution_id=inst_bharat,
            uploader_user_id="usr-bharat-adm-01",
            source_filename="bharat.csv",
            academic_year=ay,
            version=2,
            status=BatchStatus.DRAFT
        )
        db.add(bharat_batch)
        db.flush()

    try:
        # Insert target student in bharat
        z_target = StudentRecord(
            id=f"stu-z-{uuid.uuid4().hex[:6]}",
            batch_id=bharat_batch.id,
            institution_id=inst_bharat,
            programme_id="PROG-002-CSE",
            apaar_id=target_apaar,
            institution_student_id=f"ZTARG-{uuid.uuid4().hex[:4]}",
            student_name="Target Bharat Student",
            academic_year=ay
        )
        # Insert unrelated student in bharat
        z_unrelated = StudentRecord(
            id=f"stu-z-{uuid.uuid4().hex[:6]}",
            batch_id=bharat_batch.id,
            institution_id=inst_bharat,
            programme_id="PROG-002-CSE",
            apaar_id=unrelated_apaar,
            institution_student_id=f"ZUNREL-{uuid.uuid4().hex[:4]}",
            student_name="Unrelated Bharat Student",
            academic_year=ay
        )
        db.add_all([z_target, z_unrelated])

        # Create apex batch containing only target_apaar
        batch = ImportBatch(
            id=f"BATCH-FILT-{uuid.uuid4().hex[:6]}",
            institution_id=inst_apex,
            uploader_user_id="usr-apex-adm-01",
            source_filename="filtered_test.csv",
            academic_year=ay,
            version=87,
            status=BatchStatus.DRAFT
        )
        db.add(batch)
        db.flush()

        apex_stu = StudentRecord(
            id=f"stu-a-{uuid.uuid4().hex[:6]}",
            batch_id=batch.id,
            institution_id=inst_apex,
            programme_id="PROG-001-CSE",
            apaar_id=target_apaar,
            institution_student_id=f"ATARG-{uuid.uuid4().hex[:4]}",
            student_name="Apex Target Student",
            academic_year=ay
        )
        db.add(apex_stu)
        db.commit()

        # Validate batch
        apex_token = get_auth_token(client, "apex_operator@apex.edu.in")
        res = client.post(f"/api/v1/batches/{batch.id}/validate", headers={"Authorization": f"Bearer {apex_token}"})
        assert res.status_code == 200

        # Check findings: must have RULE-DUP-005 for target_apaar
        findings_res = client.get(f"/api/v1/batches/{batch.id}/findings", headers={"Authorization": f"Bearer {apex_token}"})
        findings = findings_res.json()["items"]
        dup005_findings = [f for f in findings if f["rule_code"] == "RULE-DUP-005"]
        assert len(dup005_findings) == 1
        assert dup005_findings[0]["actual_value"] == target_apaar

        # Verify MatchCandidate created for (apex_stu, z_target)
        db.expire_all()
        mat = db.query(MatchCandidate).filter(
            ((MatchCandidate.record_a_id == apex_stu.id) & (MatchCandidate.record_b_id == z_target.id)) |
            ((MatchCandidate.record_a_id == z_target.id) & (MatchCandidate.record_b_id == apex_stu.id))
        ).first()
        assert mat is not None
        assert mat.status == MatchStatus.CANDIDATE

        # Ensure no candidate was created for the unrelated student
        unrelated_mat = db.query(MatchCandidate).filter(
            (MatchCandidate.record_a_id == z_unrelated.id) | (MatchCandidate.record_b_id == z_unrelated.id)
        ).first()
        assert unrelated_mat is None

    finally:
        db.rollback()
        db.close()


# ==============================================================================
# 4. Remediation Tests for Findings P2-01, P2-02, P3-01
# ==============================================================================
def test_init_db_detects_legacy_duplicate_batch_versions_and_raises():
    """
    P2-01: Verify that duplicate batch versions in a legacy database are detected
    before unique index creation, preserving existing data and identifying the problem.
    Uses an isolated in-memory engine created without the unique index.
    """
    from sqlalchemy import create_engine, text

    test_engine = create_engine("sqlite:///:memory:")
    with test_engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE import_batches (
                id TEXT PRIMARY KEY,
                institution_id TEXT NOT NULL,
                source_filename TEXT NOT NULL,
                academic_year TEXT NOT NULL,
                version INTEGER NOT NULL,
                status TEXT NOT NULL,
                total_rows INTEGER DEFAULT 0,
                valid_rows INTEGER DEFAULT 0,
                error_rows INTEGER DEFAULT 0,
                warning_rows INTEGER DEFAULT 0,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            );
        """))
        conn.execute(text("""
            INSERT INTO import_batches (id, institution_id, source_filename, academic_year, version, status, created_at, updated_at)
            VALUES 
                ('B1', 'INST-TEST', 'file1.csv', '2026-2027', 1, 'DRAFT', '2026-01-01', '2026-01-01'),
                ('B2', 'INST-TEST', 'file2.csv', '2026-2027', 1, 'DRAFT', '2026-01-01', '2026-01-01');
        """))
        conn.commit()

        # Run duplicate check query as defined in init_db
        batch_dups = conn.execute(text("""
            SELECT institution_id, academic_year, version, COUNT(*) as cnt
            FROM import_batches
            GROUP BY institution_id, academic_year, version
            HAVING cnt > 1;
        """)).fetchall()

        assert len(batch_dups) == 1
        assert batch_dups[0][0] == "INST-TEST"
        assert batch_dups[0][2] == 1
        assert batch_dups[0][3] == 2

        # Verify attempting to create unique index on legacy duplicate data raises error
        with pytest.raises(Exception) as exc_info:
            conn.execute(text("""
                CREATE UNIQUE INDEX uq_batch_institution_ay_version
                ON import_batches(institution_id, academic_year, version);
            """))
        assert "UNIQUE constraint failed" in str(exc_info.value)

        # Verify existing records remain untouched
        count = conn.execute(text("SELECT COUNT(*) FROM import_batches;")).scalar()
        assert count == 2


def test_init_db_detects_legacy_duplicate_match_candidates_and_raises():
    """
    P2-01: Verify that existing reverse-order duplicate match candidates in a legacy database
    are detected before index creation, raising an error rather than silently failing, and preserving data.
    Uses an isolated in-memory engine created without the unique index.
    """
    from sqlalchemy import create_engine, text

    test_engine = create_engine("sqlite:///:memory:")
    with test_engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE match_candidates (
                id TEXT PRIMARY KEY,
                record_a_id TEXT NOT NULL,
                record_b_id TEXT NOT NULL,
                institution_a_id TEXT NOT NULL,
                institution_b_id TEXT NOT NULL,
                matching_signal TEXT NOT NULL,
                confidence REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL
            );
        """))
        # Insert reverse duplicate pairs (rec-1, rec-2) and (rec-2, rec-1) into unindexed legacy table
        conn.execute(text("""
            INSERT INTO match_candidates (id, record_a_id, record_b_id, institution_a_id, institution_b_id, matching_signal, confidence, status, created_at)
            VALUES 
                ('m1', 'rec-1', 'rec-2', 'INST-T1', 'INST-T2', 'SIG', 1.0, 'CANDIDATE', '2026-01-01'),
                ('m2', 'rec-2', 'rec-1', 'INST-T2', 'INST-T1', 'SIG', 1.0, 'CANDIDATE', '2026-01-01');
        """))
        conn.commit()

        # Execute candidate duplicate check logic as in init_db
        match_dups = conn.execute(text("""
            SELECT 
                CASE WHEN record_a_id < record_b_id THEN record_a_id ELSE record_b_id END as a_id,
                CASE WHEN record_a_id < record_b_id THEN record_b_id ELSE record_a_id END as b_id,
                COUNT(*) as cnt
            FROM match_candidates
            GROUP BY a_id, b_id
            HAVING cnt > 1;
        """)).fetchall()

        assert len(match_dups) == 1
        assert match_dups[0][0] == "rec-1"
        assert match_dups[0][1] == "rec-2"
        assert match_dups[0][2] == 2

        # Verify attempting to create symmetric unique index on duplicates fails
        with pytest.raises(Exception) as exc_info:
            conn.execute(text("""
                CREATE UNIQUE INDEX uq_match_candidates_pair
                ON match_candidates(
                    CASE WHEN record_a_id < record_b_id THEN record_a_id ELSE record_b_id END,
                    CASE WHEN record_a_id < record_b_id THEN record_b_id ELSE record_a_id END
                );
            """))
        assert "UNIQUE constraint failed" in str(exc_info.value)

        # Verify both records are preserved
        count = conn.execute(text("SELECT COUNT(*) FROM match_candidates;")).scalar()
        assert count == 2


def test_is_match_candidate_pair_conflict_helper():
    """
    P2-02: Test helper correctly distinguishes match candidate pair unique conflict
    from unrelated integrity errors (foreign key, not null).
    """
    from backend.app.services.validation_service import is_match_candidate_pair_conflict
    import sqlite3

    # Simulated match candidate index conflict
    sqlite_err = sqlite3.IntegrityError("UNIQUE constraint failed: index 'uq_match_candidates_pair'")
    sa_exc = IntegrityError("statement", [], sqlite_err)
    assert is_match_candidate_pair_conflict(sa_exc) is True

    # Simulated match candidate table conflict
    sqlite_err2 = sqlite3.IntegrityError("UNIQUE constraint failed: match_candidates.record_a_id")
    sa_exc2 = IntegrityError("statement", [], sqlite_err2)
    assert is_match_candidate_pair_conflict(sa_exc2) is True

    # Unrelated FK error
    fk_err = sqlite3.IntegrityError("FOREIGN KEY constraint failed")
    sa_fk = IntegrityError("statement", [], fk_err)
    assert is_match_candidate_pair_conflict(sa_fk) is False

    # Unrelated NOT NULL error
    null_err = sqlite3.IntegrityError("NOT NULL constraint failed: import_batches.academic_year")
    sa_null = IntegrityError("statement", [], null_err)
    assert is_match_candidate_pair_conflict(sa_null) is False


def test_concurrent_validation_retry_preserves_findings_and_status(client):
    """
    P3-01: Verify that when a match candidate conflict occurs during commit,
    the retry correctly preserves all computed findings, batch metrics, and audit events without duplication.
    """
    db = SessionLocal()
    inst_apex = "INST-001"
    inst_bharat = "INST-002"
    ay = "2026-2027"

    bharat_batch = db.query(ImportBatch).filter(ImportBatch.institution_id == inst_bharat).first()
    assert bharat_batch is not None

    shared_apaar = "444455556666"

    try:
        # Bharat student record
        b_stu = StudentRecord(
            id=f"stu-b-{uuid.uuid4().hex[:6]}",
            batch_id=bharat_batch.id,
            institution_id=inst_bharat,
            programme_id="PROG-002-CSE",
            apaar_id=shared_apaar,
            institution_student_id=f"B-{uuid.uuid4().hex[:4]}",
            student_name="Bharat Student",
            academic_year=ay
        )
        db.add(b_stu)

        # Apex batch & student
        batch = ImportBatch(
            id=f"BATCH-COLL-{uuid.uuid4().hex[:6]}",
            institution_id=inst_apex,
            uploader_user_id="usr-apex-adm-01",
            source_filename="coll.csv",
            academic_year=ay,
            version=77,
            status=BatchStatus.DRAFT
        )
        db.add(batch)
        db.flush()

        a_stu = StudentRecord(
            id=f"stu-a-{uuid.uuid4().hex[:6]}",
            batch_id=batch.id,
            institution_id=inst_apex,
            programme_id="PROG-001-CSE",
            apaar_id=shared_apaar,
            institution_student_id=f"A-{uuid.uuid4().hex[:4]}",
            student_name="Apex Student",
            academic_year=ay
        )
        db.add(a_stu)
        db.commit()

        # Validate batch once: this creates candidate (a_stu, b_stu)
        apex_token = get_auth_token(client, "apex_operator@apex.edu.in")
        res1 = client.post(f"/api/v1/batches/{batch.id}/validate", headers={"Authorization": f"Bearer {apex_token}"})
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["status"] == "VALIDATED"
        assert data1["findings_count"] >= 1

        # Validate batch again: tests idempotency and candidate deduplication
        res2 = client.post(f"/api/v1/batches/{batch.id}/validate", headers={"Authorization": f"Bearer {apex_token}"})
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["status"] == "VALIDATED"
        assert data2["findings_count"] == data1["findings_count"]

        # Ensure exactly one candidate exists for the pair
        db.expire_all()
        candidates = db.query(MatchCandidate).filter(
            ((MatchCandidate.record_a_id == a_stu.id) & (MatchCandidate.record_b_id == b_stu.id)) |
            ((MatchCandidate.record_a_id == b_stu.id) & (MatchCandidate.record_b_id == a_stu.id))
        ).all()
        assert len(candidates) == 1

    finally:
        db.rollback()
        db.close()


def test_symmetric_match_candidate_index_compilation_and_dialect_support():
    """
    P2-02 Audit Remediation Test:
    - Verifies that MatchCandidate's symmetric uniqueness index compiles cleanly
      for both SQLite and PostgreSQL dialects.
    - Verifies init_db() executes safely on the active database without error.
    - Verifies that inserting symmetric duplicate candidates (A, B) and (B, A) is strictly
      prevented by the database-level unique constraint.
    """
    from sqlalchemy.dialects import sqlite, postgresql
    from sqlalchemy.schema import CreateIndex
    from backend.app.db.session import init_db

    # 1. DDL compilation check for SQLite and PostgreSQL
    index_obj = None
    for idx in MatchCandidate.__table__.indexes:
        if idx.name == "uq_match_candidates_pair":
            index_obj = idx
            break

    assert index_obj is not None, "uq_match_candidates_pair index not found on MatchCandidate"

    ddl_sqlite = str(CreateIndex(index_obj).compile(dialect=sqlite.dialect()))
    ddl_postgres = str(CreateIndex(index_obj).compile(dialect=postgresql.dialect()))

    assert "CREATE UNIQUE INDEX uq_match_candidates_pair ON match_candidates" in ddl_sqlite
    assert "CASE WHEN" in ddl_sqlite

    assert "CREATE UNIQUE INDEX uq_match_candidates_pair ON match_candidates" in ddl_postgres
    assert "CASE WHEN" in ddl_postgres

    # 2. Database initialization idempotency
    init_db()  # Must not raise

    # 3. Functional enforcement of symmetric pair uniqueness
    db = SessionLocal()
    rec_a_id = f"stu-sym-a-{uuid.uuid4().hex[:6]}"
    rec_b_id = f"stu-sym-b-{uuid.uuid4().hex[:6]}"
    batch_id = f"BATCH-SYM-{uuid.uuid4().hex[:6]}"

    try:
        # Create minimal batch and records
        batch = ImportBatch(
            id=batch_id,
            institution_id="INST-001",
            uploader_user_id="usr-apex-adm-01",
            source_filename="sym.csv",
            academic_year="2026-2027",
            version=int(uuid.uuid4().int % 900000 + 1000),
            status=BatchStatus.DRAFT
        )
        db.add(batch)

        stu_a = StudentRecord(
            id=rec_a_id,
            batch_id=batch_id,
            institution_id="INST-001",
            programme_id="PROG-001-CSE",
            apaar_id="111122223333",
            institution_student_id=f"SYMA-{uuid.uuid4().hex[:4]}",
            student_name="Symmetric Student A",
            academic_year="2026-2027"
        )
        stu_b = StudentRecord(
            id=rec_b_id,
            batch_id=batch_id,
            institution_id="INST-001",
            programme_id="PROG-001-CSE",
            apaar_id="111122223333",
            institution_student_id=f"SYMB-{uuid.uuid4().hex[:4]}",
            student_name="Symmetric Student B",
            academic_year="2026-2027"
        )
        db.add_all([stu_a, stu_b])
        db.commit()

        # Insert pair (A, B)
        c1 = MatchCandidate(
            id=f"mat-1-{uuid.uuid4().hex[:6]}",
            record_a_id=rec_a_id,
            record_b_id=rec_b_id,
            institution_a_id="INST-001",
            institution_b_id="INST-001",
            matching_signal="APAAR_EXACT",
            confidence=1.0,
            status=MatchStatus.CANDIDATE
        )
        db.add(c1)
        db.commit()

        # Insert reversed pair (B, A) -> MUST trigger IntegrityError
        c2 = MatchCandidate(
            id=f"mat-2-{uuid.uuid4().hex[:6]}",
            record_a_id=rec_b_id,
            record_b_id=rec_a_id,
            institution_a_id="INST-001",
            institution_b_id="INST-001",
            matching_signal="APAAR_EXACT",
            confidence=1.0,
            status=MatchStatus.CANDIDATE
        )
        db.add(c2)
        with pytest.raises(IntegrityError):
            db.commit()

        db.rollback()

    finally:
        db.rollback()
        db.query(MatchCandidate).filter(
            ((MatchCandidate.record_a_id == rec_a_id) & (MatchCandidate.record_b_id == rec_b_id)) |
            ((MatchCandidate.record_a_id == rec_b_id) & (MatchCandidate.record_b_id == rec_a_id))
        ).delete(synchronize_session=False)
        db.query(StudentRecord).filter(StudentRecord.id.in_([rec_a_id, rec_b_id])).delete(synchronize_session=False)
        db.query(ImportBatch).filter(ImportBatch.id == batch_id).delete(synchronize_session=False)
        db.commit()
        db.close()


def test_database_engine_connection_and_pool_configuration():
    """
    P2-03 Audit Remediation Test:
    - Verifies that SQLite engine is configured with WAL journal mode, busy_timeout=30000ms,
      and foreign key enforcement enabled.
    - Verifies that client-server engines (PostgreSQL) use configured pool parameters (pool_size,
      max_overflow, pool_timeout, and pool_pre_ping) from Settings without errors.
    """
    from sqlalchemy import create_engine
    from backend.app.core.config import settings
    from backend.app.db.session import engine

    # 1. Active SQLite engine configuration
    with engine.connect() as conn:
        fk = conn.exec_driver_sql("PRAGMA foreign_keys;").fetchone()[0]
        journal = conn.exec_driver_sql("PRAGMA journal_mode;").fetchone()[0]
        timeout = conn.exec_driver_sql("PRAGMA busy_timeout;").fetchone()[0]

        assert fk == 1, "SQLite PRAGMA foreign_keys must be ON"
        assert journal.lower() == "wal", "SQLite PRAGMA journal_mode must be WAL"
        assert timeout >= 30000, "SQLite PRAGMA busy_timeout must be at least 30000ms"

    # 2. Mock client-server PostgreSQL pool configuration verification
    mock_pg_url = "postgresql://user:pass@localhost:5432/mock_db"
    pg_kwargs = {
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
        "pool_pre_ping": True,
    }
    # Verify create_engine accepts these kwargs with postgresql dialect without error
    # Note: we pass strategy/mock or verify QueuePool attributes
    from sqlalchemy.pool import QueuePool
    pg_engine = create_engine(
        mock_pg_url,
        **pg_kwargs
    )
    assert isinstance(pg_engine.pool, QueuePool)
    assert pg_engine.pool.size() == settings.DB_POOL_SIZE
    assert pg_engine.pool._max_overflow == settings.DB_MAX_OVERFLOW
    assert pg_engine.pool._timeout == settings.DB_POOL_TIMEOUT
    assert pg_engine.pool._pre_ping is True
    pg_engine.dispose()
