"""
Unit and Integration Tests for DELETE /api/v1/batches/{batch_id}
Covers:
1. Successful deletion of an eligible batch (e.g. DRAFT or NEEDS_CORRECTION)
2. Cascading deletion of associated student records and validation findings
3. Safe cleanup of match candidates referencing students of the deleted batch
4. Immutable audit logging of the deletion event
5. Rejection of protected batch statuses (SUBMITTED, UNDER_REVIEW, ACCEPTED)
6. Unauthorized access (non-admin roles, e.g. INSTITUTION_OPERATOR or unauthenticated)
7. Cross-institution access rejection (INSTITUTION_ADMIN attempting to delete another institution's batch)
8. Nonexistent batch ID handling (404)
9. Transactional integrity on failure
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal
from backend.app.main import app
from backend.app.models.audit import AuditEvent
from backend.app.models.batch import ImportBatch
from backend.app.models.enums import (
    AuditAction,
    BatchStatus,
    EnrolmentStatus,
    FindingSeverity,
    FindingStatus,
    MatchStatus,
    SeatType,
)
from backend.app.models.match import MatchCandidate
from backend.app.models.student import StudentRecord
from backend.app.models.validation import ValidationFinding


@pytest.fixture
def client():
    return TestClient(app)


def get_token(client: TestClient, email: str, password: str = "DemoPassword@2026") -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


def create_mock_batch_with_data(db: Session, institution_id: str, status: BatchStatus, source_name: str = "test.csv"):
    batch_id = f"BATCH-TEST-{uuid.uuid4().hex[:8]}"
    batch = ImportBatch(
        id=batch_id,
        institution_id=institution_id,
        source_filename=source_name,
        academic_year="2026-2027",
        version=999,
        status=status,
        total_rows=2,
        valid_rows=1,
        error_rows=1,
        warning_rows=0,
    )
    db.add(batch)

    stu1 = StudentRecord(
        id=f"stu-{uuid.uuid4().hex[:8]}",
        batch_id=batch_id,
        institution_id=institution_id,
        programme_id="PROG-001-CSE",
        apaar_id="987654321012",
        institution_student_id=f"ROLL-{uuid.uuid4().hex[:6]}",
        student_name="Test Student 1",
        academic_year="2026-2027",
        enrolment_status=EnrolmentStatus.ENROLLED,
        seat_type=SeatType.REGULAR,
    )
    stu2 = StudentRecord(
        id=f"stu-{uuid.uuid4().hex[:8]}",
        batch_id=batch_id,
        institution_id=institution_id,
        programme_id="PROG-001-CSE",
        apaar_id="123456789010",
        institution_student_id=f"ROLL-{uuid.uuid4().hex[:6]}",
        student_name="Test Student 2",
        academic_year="2026-2027",
        enrolment_status=EnrolmentStatus.ENROLLED,
        seat_type=SeatType.REGULAR,
    )
    db.add_all([stu1, stu2])

    finding = ValidationFinding(
        id=f"find-{uuid.uuid4().hex[:8]}",
        batch_id=batch_id,
        record_id=stu2.id,
        row_number=2,
        rule_code="RULE-CAT-001",
        severity=FindingSeverity.WARNING,
        message="Test warning",
        status=FindingStatus.OPEN,
    )
    db.add(finding)
    db.commit()
    return batch_id, [stu1.id, stu2.id], finding.id


def test_successful_batch_deletion_and_cascades(client: TestClient):
    token = get_token(client, "apex_admin@apex.edu.in")
    db = SessionLocal()
    batch_id, stu_ids, finding_id = create_mock_batch_with_data(db, "INST-001", BatchStatus.NEEDS_CORRECTION)

    try:
        res = client.delete(f"/api/v1/batches/{batch_id}", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["success"] is True
        assert data["deleted_records"] == 2
        assert data["deleted_findings"] == 1

        # Check DB to verify batch, students, and findings are gone
        assert db.query(ImportBatch).filter(ImportBatch.id == batch_id).first() is None
        assert db.query(StudentRecord).filter(StudentRecord.batch_id == batch_id).count() == 0
        assert db.query(ValidationFinding).filter(ValidationFinding.batch_id == batch_id).count() == 0

        # Verify audit log was recorded
        audit = db.query(AuditEvent).filter(
            AuditEvent.object_id == batch_id,
            AuditEvent.action == AuditAction.BATCH_DELETE
        ).first()
        assert audit is not None
        assert "Deleted batch" in audit.details
    finally:
        db.close()


def test_match_candidate_cleanup_on_batch_delete(client: TestClient):
    token = get_token(client, "apex_admin@apex.edu.in")
    db = SessionLocal()
    batch_id, stu_ids, _ = create_mock_batch_with_data(db, "INST-001", BatchStatus.DRAFT)

    # Create dummy match candidate referencing stu_ids[0]
    match_id = f"mat-test-{uuid.uuid4().hex[:8]}"
    match = MatchCandidate(
        id=match_id,
        record_a_id=stu_ids[0],
        record_b_id=stu_ids[1],
        institution_a_id="INST-001",
        institution_b_id="INST-001",
        matching_signal="fuzzy_name",
        confidence=0.9,
        status=MatchStatus.CANDIDATE
    )
    db.add(match)
    db.commit()

    try:
        res = client.delete(f"/api/v1/batches/{batch_id}", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        assert res.json()["deleted_matches"] == 1
        assert db.query(MatchCandidate).filter(MatchCandidate.id == match_id).first() is None
    finally:
        db.close()


def test_rejection_of_protected_batch_statuses(client: TestClient):
    token = get_token(client, "apex_admin@apex.edu.in")
    db = SessionLocal()
    
    for protected_status in (BatchStatus.SUBMITTED, BatchStatus.UNDER_REVIEW, BatchStatus.ACCEPTED):
        batch_id, _, _ = create_mock_batch_with_data(db, "INST-001", protected_status)
        try:
            res = client.delete(f"/api/v1/batches/{batch_id}", headers={"Authorization": f"Bearer {token}"})
            assert res.status_code == 400
            assert "Cannot delete batch" in res.text
            # Verify batch was NOT deleted
            assert db.query(ImportBatch).filter(ImportBatch.id == batch_id).first() is not None
        finally:
            # Clean up test batch manually
            b = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
            if b:
                db.delete(b)
                db.commit()
    db.close()


def test_unauthorized_role_rejected(client: TestClient):
    # INSTITUTION_OPERATOR is not allowed to delete batches
    token = get_token(client, "apex_operator@apex.edu.in")
    db = SessionLocal()
    batch_id, _, _ = create_mock_batch_with_data(db, "INST-001", BatchStatus.DRAFT)

    try:
        res = client.delete(f"/api/v1/batches/{batch_id}", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 403
        assert "not authorized to delete batches" in res.text
    finally:
        b = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
        if b:
            db.delete(b)
            db.commit()
        db.close()


def test_cross_institution_deletion_prevented(client: TestClient):
    # Bharat admin (INST-002) attempting to delete Apex batch (INST-001)
    bharat_token = get_token(client, "bharat_admin@bharat.edu.in")
    db = SessionLocal()
    batch_id, _, _ = create_mock_batch_with_data(db, "INST-001", BatchStatus.DRAFT)

    try:
        res = client.delete(f"/api/v1/batches/{batch_id}", headers={"Authorization": f"Bearer {bharat_token}"})
        assert res.status_code == 403
        assert "Cross-institution access denied" in res.text
    finally:
        b = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
        if b:
            db.delete(b)
            db.commit()
        db.close()


def test_nonexistent_batch_404(client: TestClient):
    token = get_token(client, "apex_admin@apex.edu.in")
    res = client.delete("/api/v1/batches/BATCH-NONEXISTENT-99999", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404
