"""
Phase 4 Batch 2 Comprehensive Test Suite
Tests for:
1. Batch submission lifecycle (`POST /api/v1/batches/{id}/submit`):
   - Successful submission of VALIDATED batch transitions to SUBMITTED and logs BATCH_SUBMIT.
   - Rejection when unresolved BLOCKING_ERROR findings or error_rows > 0 exist.
   - Warning enforcement: allow_warnings=False blocks submission if WARNING findings exist; allow_warnings=True succeeds.
   - State enforcement: cannot resubmit already SUBMITTED batches.
   - RBAC & Tenant Isolation: INSTITUTION_ADMIN can submit own batch; INSTITUTION_OPERATOR rejected (403); cross-institution submission blocked (403/404).

2. Validation finding review workflow (`POST /api/v1/reviews/{finding_id}`):
   - Review finding transitions status to RESOLVED / DISMISSED and records audit event.
   - Rejects empty/missing review reason with HTTP 422.
   - Resolving a BLOCKING_ERROR on a batch decrements batch.error_rows and transitions batch to VALIDATED if 0 errors remain.
   - Isolation: Institution users cannot review findings belonging to another institution.

3. Cross-institution duplicate match candidate review (`POST /api/v1/reviews/matches/{match_id}`):
   - AICTE_ADMIN can review match candidates (CONFIRMED_DUPLICATE / DISMISSED) with mandatory review notes.
   - Institution users (INSTITUTION_ADMIN, INSTITUTION_OPERATOR) receive 403 PERMISSION_DENIED.

4. Institution dashboard API (`GET /api/v1/dashboard/institution`):
   - Aggregates batch totals, student records, valid/error counts, missing APAARs, duplicate flags, intake metrics, recent batches, recent audit activity.
   - Strictly isolated to caller's institution; non-AICTE users cannot view metrics of other institutions.

5. AICTE dashboard API (`GET /api/v1/dashboard/aicte`):
   - Aggregates national institution counts, total submissions, total batches, total approved intake, aggregate intake percentage, duplicate breakdown, per-institution summaries.
   - Restricted strictly to AICTE_ADMIN / DEMO_ADMIN; institution users receive 403 PERMISSION_DENIED.
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.session import SessionLocal
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
from backend.app.models.institution import Institution, Programme
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
def apex_operator_token(client):
    return get_auth_token(client, "apex_operator@apex.edu.in")


@pytest.fixture
def bharat_admin_token(client):
    return get_auth_token(client, "bharat_admin@bharat.edu.in")


# ==============================================================================
# 1. Batch Submission Lifecycle Tests
# ==============================================================================

def test_batch_submission_success(client: TestClient, apex_admin_token):
    """A VALIDATED batch with 0 unresolved errors submits cleanly."""
    db = SessionLocal()
    batch_id = f"BATCH-SUB-OK-{uuid.uuid4().hex[:6]}"
    batch = ImportBatch(
        id=batch_id,
        institution_id="INST-001",
        uploader_user_id="usr-apex-adm-01",
        source_filename="clean_submission.csv",
        academic_year="2026-2027",
        version=921,
        total_rows=10,
        valid_rows=10,
        error_rows=0,
        warning_rows=0,
        status=BatchStatus.VALIDATED,
    )
    db.add(batch)
    db.commit()

    try:
        response = client.post(
            f"/api/v1/batches/{batch_id}/submit",
            json={"comments": "All records validated and verified.", "allow_warnings": True},
            headers={"Authorization": f"Bearer {apex_admin_token}"},
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["batch_id"] == batch_id
        assert data["status"] == BatchStatus.SUBMITTED.value
        assert data["submitted_at"] is not None
        assert "successfully submitted" in data["message"].lower()

        # Verify batch status in DB
        db.expire_all()
        b_after = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
        assert b_after.status == BatchStatus.SUBMITTED

        # Verify audit log
        audit = db.query(AuditEvent).filter(
            AuditEvent.object_id == batch_id,
            AuditEvent.action == AuditAction.BATCH_SUBMIT
        ).first()
        assert audit is not None
        assert audit.institution_id == "INST-001"
    finally:
        db.query(AuditEvent).filter(AuditEvent.object_id == batch_id).delete()
        db.query(ImportBatch).filter(ImportBatch.id == batch_id).delete()
        db.commit()
        db.close()


def test_batch_submission_blocked_by_unresolved_blocking_error(client: TestClient, apex_admin_token):
    """Batch cannot be submitted when unresolved BLOCKING_ERROR findings exist."""
    db = SessionLocal()
    batch_id = f"BATCH-SUB-ERR-{uuid.uuid4().hex[:6]}"
    finding_id = f"fnd-{uuid.uuid4().hex[:8]}"

    batch = ImportBatch(
        id=batch_id,
        institution_id="INST-001",
        uploader_user_id="usr-apex-adm-01",
        source_filename="errors.csv",
        academic_year="2026-2027",
        version=922,
        total_rows=5,
        valid_rows=4,
        error_rows=1,
        warning_rows=0,
        status=BatchStatus.NEEDS_CORRECTION,
    )
    db.add(batch)

    finding = ValidationFinding(
        id=finding_id,
        batch_id=batch_id,
        row_number=2,
        field_name="apaar_id",
        rule_code="RULE-APAAR-002",
        message="Invalid APAAR ID checksum",
        severity=FindingSeverity.BLOCKING_ERROR,
        status=FindingStatus.OPEN,
    )
    db.add(finding)
    db.commit()

    try:
        response = client.post(
            f"/api/v1/batches/{batch_id}/submit",
            json={"comments": "Attempting submission with open error"},
            headers={"Authorization": f"Bearer {apex_admin_token}"},
        )
        assert response.status_code == 400
        assert "blocking error" in response.json()["error"]["message"].lower()
    finally:
        db.query(ValidationFinding).filter(ValidationFinding.id == finding_id).delete()
        db.query(ImportBatch).filter(ImportBatch.id == batch_id).delete()
        db.commit()
        db.close()


def test_batch_submission_warning_flag_enforcement(client: TestClient, apex_admin_token):
    """When allow_warnings=False, submission fails if open WARNING findings exist."""
    db = SessionLocal()
    batch_id = f"BATCH-SUB-WARN-{uuid.uuid4().hex[:6]}"
    finding_id = f"fnd-{uuid.uuid4().hex[:8]}"

    batch = ImportBatch(
        id=batch_id,
        institution_id="INST-001",
        uploader_user_id="usr-apex-adm-01",
        source_filename="warnings.csv",
        academic_year="2026-2027",
        version=923,
        total_rows=5,
        valid_rows=5,
        error_rows=0,
        warning_rows=1,
        status=BatchStatus.VALIDATED,
    )
    db.add(batch)

    finding = ValidationFinding(
        id=finding_id,
        batch_id=batch_id,
        row_number=1,
        field_name="student_category",
        rule_code="RULE-CAT-001",
        message="Category quota mismatch",
        severity=FindingSeverity.WARNING,
        status=FindingStatus.OPEN,
    )
    db.add(finding)
    db.commit()

    try:
        # Case A: Disallow warnings -> 400
        res_disallow = client.post(
            f"/api/v1/batches/{batch_id}/submit",
            json={"comments": "No warnings allowed", "allow_warnings": False},
            headers={"Authorization": f"Bearer {apex_admin_token}"},
        )
        assert res_disallow.status_code == 400
        assert "warning" in res_disallow.json()["error"]["message"].lower()

        # Case B: Allow warnings -> 200
        res_allow = client.post(
            f"/api/v1/batches/{batch_id}/submit",
            json={"comments": "Warnings acknowledged", "allow_warnings": True},
            headers={"Authorization": f"Bearer {apex_admin_token}"},
        )
        assert res_allow.status_code == 200
        assert res_allow.json()["status"] == BatchStatus.SUBMITTED.value
    finally:
        db.query(AuditEvent).filter(AuditEvent.object_id == batch_id).delete()
        db.query(ValidationFinding).filter(ValidationFinding.id == finding_id).delete()
        db.query(ImportBatch).filter(ImportBatch.id == batch_id).delete()
        db.commit()
        db.close()


def test_batch_submission_invalid_initial_state(client: TestClient, apex_admin_token):
    """Batch in already SUBMITTED state cannot be resubmitted."""
    db = SessionLocal()
    batch_id = f"BATCH-SUB-RESUB-{uuid.uuid4().hex[:6]}"

    batch = ImportBatch(
        id=batch_id,
        institution_id="INST-001",
        uploader_user_id="usr-apex-adm-01",
        source_filename="draft.csv",
        academic_year="2026-2027",
        version=924,
        total_rows=1,
        valid_rows=1,
        error_rows=0,
        status=BatchStatus.SUBMITTED,
    )
    db.add(batch)
    db.commit()

    try:
        response = client.post(
            f"/api/v1/batches/{batch_id}/submit",
            json={"comments": "Resubmission attempt"},
            headers={"Authorization": f"Bearer {apex_admin_token}"},
        )
        assert response.status_code == 400
        assert "already been submitted" in response.json()["error"]["message"].lower()

    finally:
        db.query(ImportBatch).filter(ImportBatch.id == batch_id).delete()
        db.commit()
        db.close()


def test_batch_submission_permissions_and_cross_institution_isolation(
    client: TestClient, apex_operator_token, bharat_admin_token
):
    """Operators cannot submit batches, and Bharat admin cannot submit Apex's batch."""
    db = SessionLocal()
    batch_id = f"BATCH-SUB-ISO-{uuid.uuid4().hex[:6]}"

    batch = ImportBatch(
        id=batch_id,
        institution_id="INST-001",
        uploader_user_id="usr-apex-adm-01",
        source_filename="perm_test.csv",
        academic_year="2026-2027",
        version=925,
        total_rows=1,
        valid_rows=1,
        error_rows=0,
        status=BatchStatus.VALIDATED,
    )
    db.add(batch)
    db.commit()

    try:
        # Operator cannot submit (403)
        res_op = client.post(
            f"/api/v1/batches/{batch_id}/submit",
            json={"comments": "Operator trying to submit"},
            headers={"Authorization": f"Bearer {apex_operator_token}"},
        )
        assert res_op.status_code == 403

        # Bharat admin cannot submit Apex's batch (403)
        res_cross = client.post(
            f"/api/v1/batches/{batch_id}/submit",
            json={"comments": "Bharat trying to submit Apex batch"},
            headers={"Authorization": f"Bearer {bharat_admin_token}"},
        )
        assert res_cross.status_code == 403
    finally:
        db.query(ImportBatch).filter(ImportBatch.id == batch_id).delete()
        db.commit()
        db.close()


# ==============================================================================
# 2. Finding Review Workflow Tests
# ==============================================================================

def test_finding_review_resolved_updates_error_counters(client: TestClient, apex_admin_token):
    """Reviewing and resolving a blocking finding decrements batch error_rows."""
    db = SessionLocal()
    batch_id = f"BATCH-REV-OK-{uuid.uuid4().hex[:6]}"
    finding_id = f"fnd-{uuid.uuid4().hex[:8]}"

    batch = ImportBatch(
        id=batch_id,
        institution_id="INST-001",
        uploader_user_id="usr-apex-adm-01",
        source_filename="review_test.csv",
        academic_year="2026-2027",
        version=930,
        total_rows=5,
        valid_rows=4,
        error_rows=1,
        warning_rows=0,
        status=BatchStatus.NEEDS_CORRECTION,
    )
    db.add(batch)

    finding = ValidationFinding(
        id=finding_id,
        batch_id=batch_id,
        row_number=3,
        field_name="student_name",
        rule_code="RULE-REQ-001",
        message="Student name is missing",
        severity=FindingSeverity.BLOCKING_ERROR,
        status=FindingStatus.OPEN,
    )
    db.add(finding)
    db.commit()

    try:
        # Review as RESOLVED
        res = client.post(
            f"/api/v1/reviews/{finding_id}",
            json={"decision": "RESOLVED", "reason": "Student verified against physical admission register."},
            headers={"Authorization": f"Bearer {apex_admin_token}"},
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["status"] == "RESOLVED"
        assert data["reason"] == "Student verified against physical admission register."
        assert data["reviewed_by"] == "apex_admin@apex.edu.in"

        # Check batch error_rows decremented and status transitioned to VALIDATED
        db.expire_all()
        b_after = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
        assert b_after.error_rows == 0
        assert b_after.status == BatchStatus.VALIDATED

        # Verify audit log
        audit = db.query(AuditEvent).filter(
            AuditEvent.object_id == finding_id,
            AuditEvent.action == AuditAction.REVIEW_DECISION
        ).first()
        assert audit is not None
    finally:
        db.query(AuditEvent).filter(AuditEvent.object_id == finding_id).delete()
        db.query(ValidationFinding).filter(ValidationFinding.id == finding_id).delete()
        db.query(ImportBatch).filter(ImportBatch.id == batch_id).delete()
        db.commit()
        db.close()


def test_finding_review_requires_non_empty_reason(client: TestClient, apex_admin_token):
    """Review reason cannot be empty or shorter than 3 characters."""
    db = SessionLocal()
    batch_id = f"BATCH-REV-RSN-{uuid.uuid4().hex[:6]}"
    finding_id = f"fnd-{uuid.uuid4().hex[:8]}"

    batch = ImportBatch(
        id=batch_id,
        institution_id="INST-001",
        uploader_user_id="usr-apex-adm-01",
        source_filename="reason_test.csv",
        academic_year="2026-2027",
        version=931,
        total_rows=1,
        valid_rows=1,
        error_rows=0,
        status=BatchStatus.VALIDATED,
    )
    db.add(batch)

    finding = ValidationFinding(
        id=finding_id,
        batch_id=batch_id,
        row_number=1,
        field_name="apaar_id",
        rule_code="RULE-APAAR-001",
        message="APAAR is missing",
        severity=FindingSeverity.INFO,
        status=FindingStatus.OPEN,
    )
    db.add(finding)
    db.commit()

    try:
        res = client.post(
            f"/api/v1/reviews/{finding_id}",
            json={"decision": "DISMISSED", "reason": "ab"},  # min_length=3
            headers={"Authorization": f"Bearer {apex_admin_token}"},
        )
        assert res.status_code == 422
    finally:
        db.query(ValidationFinding).filter(ValidationFinding.id == finding_id).delete()
        db.query(ImportBatch).filter(ImportBatch.id == batch_id).delete()
        db.commit()
        db.close()


def test_finding_review_cross_institution_forbidden(client: TestClient, bharat_admin_token):
    """Bharat administrator cannot review findings from Apex's batch."""
    db = SessionLocal()
    batch_id = f"BATCH-REV-CROSS-{uuid.uuid4().hex[:6]}"
    finding_id = f"fnd-{uuid.uuid4().hex[:8]}"

    batch = ImportBatch(
        id=batch_id,
        institution_id="INST-001",
        uploader_user_id="usr-apex-adm-01",
        source_filename="bharat_block.csv",
        academic_year="2026-2027",
        version=932,
        total_rows=1,
        valid_rows=1,
        error_rows=0,
        status=BatchStatus.VALIDATED,
    )
    db.add(batch)

    finding = ValidationFinding(
        id=finding_id,
        batch_id=batch_id,
        row_number=1,
        field_name="apaar_id",
        rule_code="RULE-TEST-001",
        message="Test finding",
        severity=FindingSeverity.INFO,
        status=FindingStatus.OPEN,
    )
    db.add(finding)
    db.commit()

    try:
        res = client.post(
            f"/api/v1/reviews/{finding_id}",
            json={"decision": "DISMISSED", "reason": "Attempted cross-institution review"},
            headers={"Authorization": f"Bearer {bharat_admin_token}"},
        )
        assert res.status_code == 403
    finally:
        db.query(ValidationFinding).filter(ValidationFinding.id == finding_id).delete()
        db.query(ImportBatch).filter(ImportBatch.id == batch_id).delete()
        db.commit()
        db.close()


# ==============================================================================
# 3. Match Candidate Review Tests
# ==============================================================================

def test_match_candidate_review_by_aicte_admin(client: TestClient, aicte_token):
    """AICTE_ADMIN reviews cross-institution duplicate match candidate."""
    db = SessionLocal()
    batch1_id = f"BATCH-MAT1-{uuid.uuid4().hex[:6]}"
    batch2_id = f"BATCH-MAT2-{uuid.uuid4().hex[:6]}"
    rec_a_id = f"stu-{uuid.uuid4().hex[:8]}"
    rec_b_id = f"stu-{uuid.uuid4().hex[:8]}"
    match_id = f"mat-{uuid.uuid4().hex[:8]}"

    b1 = ImportBatch(id=batch1_id, institution_id="INST-001", source_filename="b1.csv", academic_year="2026-2027", version=941)
    b2 = ImportBatch(id=batch2_id, institution_id="INST-002", source_filename="b2.csv", academic_year="2026-2027", version=941)
    db.add_all([b1, b2])

    rec_a = StudentRecord(
        id=rec_a_id,
        batch_id=batch1_id,
        institution_id="INST-001",
        programme_id="PROG-001-CSE",
        academic_year="2026-2027",
        institution_student_id="APEX-M-01",
        student_name="Candidate Student",
        apaar_id="987654321012",
        enrolment_status=EnrolmentStatus.ENROLLED,
        seat_type=SeatType.REGULAR,
    )
    rec_b = StudentRecord(
        id=rec_b_id,
        batch_id=batch2_id,
        institution_id="INST-002",
        programme_id="PROG-002-CSE",
        academic_year="2026-2027",
        institution_student_id="BHARAT-M-01",
        student_name="Candidate Student",
        apaar_id="987654321012",
        enrolment_status=EnrolmentStatus.ENROLLED,
        seat_type=SeatType.REGULAR,
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
        res = client.post(
            f"/api/v1/reviews/matches/{match_id}",
            json={"status": "CONFIRMED_DUPLICATE", "resolution_reason": "Confirmed dual enrolment across institutions"},
            headers={"Authorization": f"Bearer {aicte_token}"},
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["status"] == MatchStatus.CONFIRMED_DUPLICATE.value
        assert data["resolution_reason"] == "Confirmed dual enrolment across institutions"
        assert data["reviewed_by"] is not None

        # Verify audit event
        audit = db.query(AuditEvent).filter(
            AuditEvent.object_id == match_id,
            AuditEvent.action == AuditAction.REVIEW_DECISION
        ).first()
        assert audit is not None
    finally:
        db.query(AuditEvent).filter(AuditEvent.object_id == match_id).delete()
        db.query(MatchCandidate).filter(MatchCandidate.id == match_id).delete()
        db.query(StudentRecord).filter(StudentRecord.id.in_([rec_a_id, rec_b_id])).delete()
        db.query(ImportBatch).filter(ImportBatch.id.in_([batch1_id, batch2_id])).delete()
        db.commit()
        db.close()


def test_match_candidate_review_forbidden_to_institution_admin(client: TestClient, apex_admin_token):
    """Institution administrator cannot decide cross-institution match candidate."""
    db = SessionLocal()
    batch1_id = f"BATCH-MAT3-{uuid.uuid4().hex[:6]}"
    batch2_id = f"BATCH-MAT4-{uuid.uuid4().hex[:6]}"
    rec_a_id = f"stu-{uuid.uuid4().hex[:8]}"
    rec_b_id = f"stu-{uuid.uuid4().hex[:8]}"
    match_id = f"mat-{uuid.uuid4().hex[:8]}"

    b1 = ImportBatch(id=batch1_id, institution_id="INST-001", source_filename="b1.csv", academic_year="2026-2027", version=942)
    b2 = ImportBatch(id=batch2_id, institution_id="INST-002", source_filename="b2.csv", academic_year="2026-2027", version=942)
    db.add_all([b1, b2])

    rec_a = StudentRecord(
        id=rec_a_id,
        batch_id=batch1_id,
        institution_id="INST-001",
        programme_id="PROG-001-CSE",
        academic_year="2026-2027",
        institution_student_id="APEX-M-02",
        student_name="Candidate A",
        apaar_id="876543210987",
    )
    rec_b = StudentRecord(
        id=rec_b_id,
        batch_id=batch2_id,
        institution_id="INST-002",
        programme_id="PROG-002-CSE",
        academic_year="2026-2027",
        institution_student_id="BHARAT-M-02",
        student_name="Candidate B",
        apaar_id="876543210987",
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
        res = client.post(
            f"/api/v1/reviews/matches/{match_id}",
            json={"status": "DISMISSED", "resolution_reason": "Apex attempting match decision"},
            headers={"Authorization": f"Bearer {apex_admin_token}"},
        )
        assert res.status_code == 403
    finally:
        db.query(MatchCandidate).filter(MatchCandidate.id == match_id).delete()
        db.query(StudentRecord).filter(StudentRecord.id.in_([rec_a_id, rec_b_id])).delete()
        db.query(ImportBatch).filter(ImportBatch.id.in_([batch1_id, batch2_id])).delete()
        db.commit()
        db.close()


# ==============================================================================
# 4. Institution Dashboard Tests
# ==============================================================================

def test_institution_dashboard_metrics_and_isolation(client: TestClient, apex_admin_token):
    """Institution dashboard accurately reflects scoped metrics and enforces isolation."""
    res = client.get("/api/v1/dashboard/institution", headers={"Authorization": f"Bearer {apex_admin_token}"})
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["institution_id"] == "INST-001"
    assert data["institution_name"] == "Apex Institute of Technology"
    assert "total_batches" in data
    assert "total_student_records" in data
    assert "intake_utilization_pct" in data
    assert isinstance(data["programme_intake_breakdown"], list)
    assert isinstance(data["recent_batches"], list)

    # Apex user cannot access Bharat's dashboard by query parameter (403)
    res_tamper = client.get(
        "/api/v1/dashboard/institution?institution_id=INST-002",
        headers={"Authorization": f"Bearer {apex_admin_token}"},
    )
    assert res_tamper.status_code == 403


# ==============================================================================
# 5. AICTE Dashboard Tests
# ==============================================================================

def test_aicte_dashboard_metrics_and_role_protection(client: TestClient, aicte_token, apex_admin_token):
    """AICTE dashboard aggregates national figures and rejects institution users."""
    # AICTE admin access
    res = client.get("/api/v1/dashboard/aicte", headers={"Authorization": f"Bearer {aicte_token}"})
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["total_institutions"] >= 2
    assert "total_submissions" in data
    assert "total_enrolled_students" in data
    assert "total_approved_intake" in data
    assert "aggregate_intake_utilization_pct" in data
    assert "total_open_exceptions" in data
    assert "total_candidate_duplicates" in data
    assert "confirmed_duplicates_count" in data
    assert "dismissed_duplicates_count" in data
    assert isinstance(data["institution_breakdown"], list)
    assert isinstance(data["recent_activity"], list)


    # Apex admin access strictly forbidden (403)
    res_forbidden = client.get("/api/v1/dashboard/aicte", headers={"Authorization": f"Bearer {apex_admin_token}"})
    assert res_forbidden.status_code == 403
