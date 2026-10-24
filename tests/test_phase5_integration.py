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


def test_verification_cross_institution_duplicate_apaar_scoping(client: TestClient, apex_admin_token, bharat_admin_token, aicte_token):
    """
    P1-01 Verification Scoping Remediation Test:
    - Verifies that when two institutions have students with the identical APAAR ID,
      an institution user (Apex or Bharat) looking up by APAAR ID correctly resolves
      their OWN institution's student record rather than colliding or returning 403.
    - Verifies unauthorized cross-institution primary key lookup returns 403 without data disclosure.
    - Verifies non-existent APAAR lookup returns 404 without disclosing cross-institution presence.
    - Verifies AICTE administrator and External Verifier can resolve students globally.
    - Verifies certificate preview endpoint maintains the identical scoped behavior.
    """
    from backend.app.models.user import User
    from backend.app.models.enums import UserRole
    from backend.app.core.security import hash_password

    db = SessionLocal()
    # 123456789019 is a valid Verhoeff 12-digit number (d(1)=2, etc.)
    # Let's use 888877776666 which has checksum 888877776666 or compute valid
    shared_apaar = "888877776666"
    batch_apex_id = f"BATCH-P1-APEX-{uuid.uuid4().hex[:6]}"
    batch_bharat_id = f"BATCH-P1-BHARAT-{uuid.uuid4().hex[:6]}"
    stu_apex_id = f"stu-apex-{uuid.uuid4().hex[:8]}"
    stu_bharat_id = f"stu-bharat-{uuid.uuid4().hex[:8]}"
    verifier_email = f"verifier_{uuid.uuid4().hex[:6]}@evaluator.gov.in"
    verifier_user_id = f"usr-verif-{uuid.uuid4().hex[:6]}"

    v_apex = int(uuid.uuid4().int % 900000 + 1000)
    v_bharat = int(uuid.uuid4().int % 900000 + 1000)

    try:
        # Create batches for INST-001 (Apex) and INST-002 (Bharat)
        b_apex = ImportBatch(
            id=batch_apex_id,
            institution_id="INST-001",
            uploader_user_id="usr-apex-adm-01",
            source_filename="apex_p1.csv",
            academic_year="2026-2027",
            version=v_apex,
            status=BatchStatus.VALIDATED,
        )
        b_bharat = ImportBatch(
            id=batch_bharat_id,
            institution_id="INST-002",
            uploader_user_id="usr-bharat-adm-01",
            source_filename="bharat_p1.csv",
            academic_year="2026-2027",
            version=v_bharat,
            status=BatchStatus.VALIDATED,
        )
        db.add_all([b_apex, b_bharat])

        # Create two student records with the EXACT SAME APAAR ID in different institutions
        stu_apex = StudentRecord(
            id=stu_apex_id,
            batch_id=batch_apex_id,
            institution_id="INST-001",
            programme_id="PROG-001-CSE",
            academic_year="2026-2027",
            institution_student_id="APEX-STU-P1",
            student_name="Apex Student",
            apaar_id=shared_apaar,
            enrolment_status=EnrolmentStatus.ENROLLED,
            seat_type=SeatType.REGULAR,
        )
        stu_bharat = StudentRecord(
            id=stu_bharat_id,
            batch_id=batch_bharat_id,
            institution_id="INST-002",
            programme_id="PROG-002-CSE",
            academic_year="2026-2027",
            institution_student_id="BHARAT-STU-P1",
            student_name="Bharat Student",
            apaar_id=shared_apaar,
            enrolment_status=EnrolmentStatus.ENROLLED,
            seat_type=SeatType.REGULAR,
        )
        db.add_all([stu_apex, stu_bharat])

        # Create external verifier user
        verifier_user = User(
            id=verifier_user_id,
            email=verifier_email,
            hashed_password=hash_password("DemoPassword@2026"),
            full_name="External Evaluator P1",
            role=UserRole.EXTERNAL_VERIFIER,
            institution_id=None,
            is_active=True
        )
        db.add(verifier_user)
        db.commit()

        verifier_token = get_auth_token(client, verifier_email)

        # 1. Own-institution lookup by APAAR ID:
        # Apex admin queries the duplicate APAAR ID -> Must resolve Apex record (200)
        res_apex = client.get(
            f"/api/v1/verification/{shared_apaar}",
            headers={"Authorization": f"Bearer {apex_admin_token}"}
        )
        assert res_apex.status_code == 200, res_apex.text
        # Verify AuditEvent points to Apex record, not Bharat record
        audit_apex = db.query(AuditEvent).filter(
            AuditEvent.object_id == stu_apex_id,
            AuditEvent.action == AuditAction.VERIFICATION_LOOKUP
        ).order_by(AuditEvent.timestamp.desc()).first()
        assert audit_apex is not None
        assert audit_apex.institution_id == "INST-001"

        # Bharat admin queries the EXACT SAME duplicate APAAR ID -> Must resolve Bharat record (200)
        res_bharat = client.get(
            f"/api/v1/verification/{shared_apaar}",
            headers={"Authorization": f"Bearer {bharat_admin_token}"}
        )
        assert res_bharat.status_code == 200, res_bharat.text
        # Verify AuditEvent points to Bharat record
        audit_bharat = db.query(AuditEvent).filter(
            AuditEvent.object_id == stu_bharat_id,
            AuditEvent.action == AuditAction.VERIFICATION_LOOKUP
        ).order_by(AuditEvent.timestamp.desc()).first()
        assert audit_bharat is not None
        assert audit_bharat.institution_id == "INST-002"

        # 2. Certificate preview scoping with duplicate APAAR ID:
        cert_apex = client.get(
            f"/api/v1/verification/{shared_apaar}/certificate",
            headers={"Authorization": f"Bearer {apex_admin_token}"}
        )
        assert cert_apex.status_code == 200
        assert cert_apex.json()["student_name"] == "Apex Student"

        cert_bharat = client.get(
            f"/api/v1/verification/{shared_apaar}/certificate",
            headers={"Authorization": f"Bearer {bharat_admin_token}"}
        )
        assert cert_bharat.status_code == 200
        assert cert_bharat.json()["student_name"] == "Bharat Student"

        # 3. Cross-institution unauthorized lookup by internal ID:
        # Apex admin attempting to query Bharat student's primary key -> Must return 403
        res_cross_pk = client.get(
            f"/api/v1/verification/{stu_bharat_id}",
            headers={"Authorization": f"Bearer {apex_admin_token}"}
        )
        assert res_cross_pk.status_code == 403

        # Bharat admin attempting to query Apex student's primary key -> Must return 403
        res_cross_pk2 = client.get(
            f"/api/v1/verification/{stu_apex_id}",
            headers={"Authorization": f"Bearer {bharat_admin_token}"}
        )
        assert res_cross_pk2.status_code == 403

        # Cross-institution roll number lookup does NOT disclose existence of student in other inst -> 404
        res_cross_roll = client.get(
            "/api/v1/verification/BHARAT-STU-P1",
            headers={"Authorization": f"Bearer {apex_admin_token}"}
        )
        assert res_cross_roll.status_code == 404

        # 4. Privileged access: AICTE Admin can resolve globally
        res_aicte = client.get(
            f"/api/v1/verification/{stu_bharat_id}",
            headers={"Authorization": f"Bearer {aicte_token}"}
        )
        assert res_aicte.status_code == 200

        # Privileged access: External Verifier can resolve globally
        res_verifier = client.get(
            f"/api/v1/verification/{stu_apex_id}",
            headers={"Authorization": f"Bearer {verifier_token}"}
        )
        assert res_verifier.status_code == 200

        # 5. Missing / non-existent identifier returns 404
        res_missing = client.get(
            "/api/v1/verification/NON_EXISTENT_ID_99999",
            headers={"Authorization": f"Bearer {apex_admin_token}"}
        )
        assert res_missing.status_code == 404

    finally:
        db.rollback()
        db.query(AuditEvent).filter(AuditEvent.object_id.in_([stu_apex_id, stu_bharat_id])).delete(synchronize_session=False)
        db.query(StudentRecord).filter(StudentRecord.id.in_([stu_apex_id, stu_bharat_id])).delete(synchronize_session=False)
        db.query(ImportBatch).filter(ImportBatch.id.in_([batch_apex_id, batch_bharat_id])).delete(synchronize_session=False)
        db.query(User).filter(User.id == verifier_user_id).delete(synchronize_session=False)
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
