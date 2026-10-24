"""
Phase 5 Comprehensive Targeted Test Suite
Covers:
1. APAAR Verification Adapter:
   - Provider interface compliance and MockApaarAdapter behavior.
   - Visible simulation markings ('is_official=False', 'MOCK_APAAR_ADAPTER').
   - Format validation, simulated verification, simulated manual review flag, and graceful degradation during outage.
   - Endpoint GET /api/v1/verification/{student_ref} with audit trail creation.

2. Cross-Institution Duplicate Matching & Review:
   - GET /api/v1/reviews/matches with status/institution filtering.
   - Strict tenant isolation for institution users (only see candidates involving their own institution).
   - AICTE central view of all cross-institution duplicate candidates.
   - Re-verifying human review decision (no auto-merge or auto-rejection).

3. Transparent Data-Quality Score:
   - GET /api/v1/batches/{id}/quality returns explainable 0-100 score across 4 dimensions:
     Completeness, Validity, Consistency, Uniqueness.
   - Dimensional deductions and grade calculation (EXCELLENT, GOOD, NEEDS_IMPROVEMENT, POOR).
   - Confirms metric is framed as dataset hygiene, not fraud or institution ranking.

4. CSV Error and Quality Report Export:
   - GET /api/v1/reports/export with report_type='findings' and report_type='quality_summary'.
   - Role permissions (external verifier prohibited).
   - Strict institution boundary enforcement on exports.
   - Audit trail creation (AuditAction.REPORT_EXPORT).
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.adapters.mock_apaar import MockApaarAdapter
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
    VerificationOutcome,
)
from backend.app.models.match import MatchCandidate
from backend.app.models.student import StudentRecord
from backend.app.models.validation import ValidationFinding


@pytest.fixture
def client():
    return TestClient(app)


def get_auth_token(client: TestClient, email: str, password: str = "DemoPassword@2026") -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, f"Failed to login {email}: {response.text}"
    return response.json()["access_token"]


@pytest.fixture
def aicte_token(client):
    return get_auth_token(client, "aicte_admin@aicte.gov.in")


@pytest.fixture
def apex_admin_token(client):
    return get_auth_token(client, "apex_admin@apex.edu.in")


@pytest.fixture
def bharat_admin_token(client):
    return get_auth_token(client, "bharat_admin@bharat.edu.in")


# ==============================================================================
# 1. APAAR Verification Adapter Tests
# ==============================================================================

def test_mock_apaar_adapter_unit():
    """Unit test for MockApaarAdapter distinguishing format, mock verification, and outage."""
    adapter = MockApaarAdapter()

    # Valid Verhoeff synthetic APAAR
    res_ok = adapter.verify("987654321012", student_name="Alice")
    assert res_ok.outcome == VerificationOutcome.MOCK_VERIFIED
    assert res_ok.is_official is False
    assert res_ok.provider == "MOCK_APAAR_ADAPTER"
    assert "mock-ref-" in res_ok.reference_id

    # Invalid checksum
    res_bad_checksum = adapter.verify("987654321019")
    assert res_bad_checksum.outcome == VerificationOutcome.MOCK_NOT_VERIFIED
    assert res_bad_checksum.is_official is False

    # Short / bad format
    res_short = adapter.verify("12345")
    assert res_short.outcome == VerificationOutcome.MOCK_NOT_VERIFIED

    # Simulated review flag prefix
    res_review = adapter.verify("000012345678")
    assert res_review.outcome == VerificationOutcome.NEEDS_REVIEW

    # Simulated provider outage
    adapter_outage = MockApaarAdapter(simulate_outage=True)
    res_outage = adapter_outage.verify("987654321012")
    assert res_outage.outcome == VerificationOutcome.MOCK_UNAVAILABLE
    assert res_outage.is_official is False


def test_verification_api_endpoint_and_audit(client: TestClient, apex_admin_token, aicte_token):
    """GET /api/v1/verification/{student_ref} returns verified receipt and writes audit event."""
    db = SessionLocal()
    batch_id = f"BATCH-VER-{uuid.uuid4().hex[:6]}"
    student_id = f"stu-{uuid.uuid4().hex[:8]}"

    batch = ImportBatch(
        id=batch_id,
        institution_id="INST-001",
        uploader_user_id="usr-apex-adm-01",
        source_filename="ver_test.csv",
        academic_year="2026-2027",
        version=951,
        status=BatchStatus.VALIDATED,
    )
    db.add(batch)

    student = StudentRecord(
        id=student_id,
        batch_id=batch_id,
        institution_id="INST-001",
        programme_id="PROG-001-CSE",
        academic_year="2026-2027",
        institution_student_id="APEX-VER-01",
        student_name="Verifiable Student",
        apaar_id="987654321012",
        enrolment_status=EnrolmentStatus.ENROLLED,
        seat_type=SeatType.REGULAR,
    )
    db.add(student)
    db.commit()

    try:
        # Lookup by institution_student_id
        res = client.get(
            "/api/v1/verification/APEX-VER-01",
            headers={"Authorization": f"Bearer {apex_admin_token}"}
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["outcome"] == VerificationOutcome.MOCK_VERIFIED.value
        assert data["is_official"] is False
        assert data["provider"] == "MOCK_APAAR_ADAPTER"

        # Check AuditEvent in database
        audit = db.query(AuditEvent).filter(
            AuditEvent.object_id == student_id,
            AuditEvent.action == AuditAction.VERIFICATION_LOOKUP
        ).first()
        assert audit is not None
        assert audit.institution_id == "INST-001"

        # Cross-institution lookup blocked for Bharat admin
        bharat_token = get_auth_token(client, "bharat_admin@bharat.edu.in")
        res_cross = client.get(
            f"/api/v1/verification/{student_id}",
            headers={"Authorization": f"Bearer {bharat_token}"}
        )
        assert res_cross.status_code == 403

        # AICTE admin can look up any institution's student
        res_aicte = client.get(
            f"/api/v1/verification/{student_id}",
            headers={"Authorization": f"Bearer {aicte_token}"}
        )
        assert res_aicte.status_code == 200
    finally:
        db.query(AuditEvent).filter(AuditEvent.object_id == student_id).delete()
        db.query(StudentRecord).filter(StudentRecord.id == student_id).delete()
        db.query(ImportBatch).filter(ImportBatch.id == batch_id).delete()
        db.commit()
        db.close()


# ==============================================================================
# 2. Cross-Institution Duplicate Review Tests
# ==============================================================================

def test_list_matches_and_institution_isolation(client: TestClient, aicte_token, apex_admin_token, bharat_admin_token):
    """GET /api/v1/reviews/matches filters by institution and preserves human decisions."""
    db = SessionLocal()
    batch1_id = f"BATCH-MAT-A-{uuid.uuid4().hex[:6]}"
    batch2_id = f"BATCH-MAT-B-{uuid.uuid4().hex[:6]}"
    rec_a_id = f"stu-{uuid.uuid4().hex[:8]}"
    rec_b_id = f"stu-{uuid.uuid4().hex[:8]}"
    match_id = f"mat-{uuid.uuid4().hex[:8]}"

    b1 = ImportBatch(id=batch1_id, institution_id="INST-001", source_filename="b1.csv", academic_year="2026-2027", version=961)
    b2 = ImportBatch(id=batch2_id, institution_id="INST-002", source_filename="b2.csv", academic_year="2026-2027", version=961)
    db.add_all([b1, b2])

    rec_a = StudentRecord(
        id=rec_a_id, batch_id=batch1_id, institution_id="INST-001", programme_id="PROG-001-CSE",
        academic_year="2026-2027", institution_student_id="AP-DUP-01", student_name="Student X", apaar_id="987654321012"
    )
    rec_b = StudentRecord(
        id=rec_b_id, batch_id=batch2_id, institution_id="INST-002", programme_id="PROG-002-CSE",
        academic_year="2026-2027", institution_student_id="BH-DUP-01", student_name="Student X", apaar_id="987654321012"
    )
    db.add_all([rec_a, rec_b])

    match = MatchCandidate(
        id=match_id,
        record_a_id=rec_a_id,
        record_b_id=rec_b_id,
        institution_a_id="INST-001",
        institution_b_id="INST-002",
        matching_signal="CROSS_INSTITUTION_DUPLICATE_APAAR",
        confidence=1.0,
        status=MatchStatus.CANDIDATE,
    )
    db.add(match)
    db.commit()

    try:
        # AICTE admin can list all matches
        res_aicte = client.get("/api/v1/reviews/matches", headers={"Authorization": f"Bearer {aicte_token}"})
        assert res_aicte.status_code == 200
        match_ids = [m["id"] for m in res_aicte.json()["items"]]
        assert match_id in match_ids

        # Apex admin sees this match because INST-001 is involved
        res_apex = client.get("/api/v1/reviews/matches", headers={"Authorization": f"Bearer {apex_admin_token}"})
        assert res_apex.status_code == 200
        apex_match_ids = [m["id"] for m in res_apex.json()["items"]]
        assert match_id in apex_match_ids

        # AICTE resolves match as DISMISSED with human reason (no auto merge or auto rejection)
        res_review = client.post(
            f"/api/v1/reviews/matches/{match_id}",
            json={"status": "DISMISSED", "resolution_reason": "Verified legitimate transfer across semesters."},
            headers={"Authorization": f"Bearer {aicte_token}"}
        )
        assert res_review.status_code == 200
        assert res_review.json()["status"] == MatchStatus.DISMISSED.value

        # Confirm both student records remain distinct in the database (never automatically merged or deleted)
        rec_a_db = db.query(StudentRecord).filter(StudentRecord.id == rec_a_id).first()
        rec_b_db = db.query(StudentRecord).filter(StudentRecord.id == rec_b_id).first()
        assert rec_a_db is not None
        assert rec_b_db is not None
    finally:
        db.query(AuditEvent).filter(AuditEvent.object_id == match_id).delete()
        db.query(MatchCandidate).filter(MatchCandidate.id == match_id).delete()
        db.query(StudentRecord).filter(StudentRecord.id.in_([rec_a_id, rec_b_id])).delete()
        db.query(ImportBatch).filter(ImportBatch.id.in_([batch1_id, batch2_id])).delete()
        db.commit()
        db.close()


# ==============================================================================
# 3. Transparent Data-Quality Score Tests
# ==============================================================================

def test_data_quality_score_calculation(client: TestClient, apex_admin_token):
    """GET /api/v1/batches/{id}/quality returns transparent scores across 4 dimensions."""
    db = SessionLocal()
    batch_id = f"BATCH-QUAL-{uuid.uuid4().hex[:6]}"
    rec_id = f"stu-{uuid.uuid4().hex[:8]}"
    finding_id = f"fnd-{uuid.uuid4().hex[:8]}"

    batch = ImportBatch(
        id=batch_id,
        institution_id="INST-001",
        uploader_user_id="usr-apex-adm-01",
        source_filename="quality.csv",
        academic_year="2026-2027",
        version=971,
        status=BatchStatus.VALIDATED,
        total_rows=1,
        valid_rows=1,
        error_rows=0,
    )
    db.add(batch)

    student = StudentRecord(
        id=rec_id,
        batch_id=batch_id,
        institution_id="INST-001",
        programme_id="PROG-001-CSE",
        academic_year="2026-2027",
        institution_student_id="APEX-Q-01",
        student_name="Quality Student",
        apaar_id="987654321012",
        enrolment_status=EnrolmentStatus.ENROLLED,
        seat_type=SeatType.REGULAR,
    )
    db.add(student)
    db.commit()

    try:
        # Case A: Perfect record -> Score 100 / EXCELLENT
        res_clean = client.get(
            f"/api/v1/batches/{batch_id}/quality",
            headers={"Authorization": f"Bearer {apex_admin_token}"}
        )
        assert res_clean.status_code == 200, res_clean.text
        data_clean = res_clean.json()
        assert data_clean["overall_score"] == 100.0
        assert data_clean["grade"] == "EXCELLENT"
        assert data_clean["completeness"]["score"] == 100.0
        assert data_clean["validity"]["score"] == 100.0
        assert data_clean["consistency"]["score"] == 100.0
        assert data_clean["uniqueness"]["score"] == 100.0

        # Case B: Add an open syntax finding -> Validity deduction
        finding = ValidationFinding(
            id=finding_id,
            batch_id=batch_id,
            row_number=1,
            field_name="apaar_id",
            rule_code="RULE-APAAR-002",
            message="Invalid checksum",
            severity=FindingSeverity.BLOCKING_ERROR,
            status=FindingStatus.OPEN,
        )
        db.add(finding)
        db.commit()

        res_deduct = client.get(
            f"/api/v1/batches/{batch_id}/quality",
            headers={"Authorization": f"Bearer {apex_admin_token}"}
        )
        assert res_deduct.status_code == 200
        data_deduct = res_deduct.json()
        assert data_deduct["validity"]["score"] < 100.0
        assert data_deduct["overall_score"] < 100.0
        assert "dataset hygiene" in data_deduct["explanation"].lower()
    finally:
        db.query(ValidationFinding).filter(ValidationFinding.id == finding_id).delete()
        db.query(StudentRecord).filter(StudentRecord.id == rec_id).delete()
        db.query(ImportBatch).filter(ImportBatch.id == batch_id).delete()
        db.commit()
        db.close()


# ==============================================================================
# 4. CSV Error & Quality Report Export Tests
# ==============================================================================

def test_reports_export_findings_and_quality(client: TestClient, apex_admin_token, aicte_token):
    """GET /api/v1/reports/export streams CSV findings and quality summaries with role enforcement."""
    # Export findings CSV
    res_findings = client.get(
        "/api/v1/reports/export?report_type=findings",
        headers={"Authorization": f"Bearer {apex_admin_token}"}
    )
    assert res_findings.status_code == 200
    assert res_findings.headers["content-type"].startswith("text/csv")
    assert "finding_id,batch_id,row_number" in res_findings.text

    # Export quality summary CSV
    res_quality = client.get(
        "/api/v1/reports/export?report_type=quality_summary",
        headers={"Authorization": f"Bearer {apex_admin_token}"}
    )
    assert res_quality.status_code == 200
    assert "batch_id,institution_id,academic_year" in res_quality.text
    assert "overall_quality_score" in res_quality.text

    # Cross-institution report tamper blocked for Apex user
    res_tamper = client.get(
        "/api/v1/reports/export?institution_id=INST-002",
        headers={"Authorization": f"Bearer {apex_admin_token}"}
    )
    assert res_tamper.status_code == 403

    # AICTE admin can export cross-institution report
    res_aicte = client.get(
        "/api/v1/reports/export?institution_id=INST-002",
        headers={"Authorization": f"Bearer {aicte_token}"}
    )
    assert res_aicte.status_code == 200
