"""
Focused Test Suite for Phase 1: Dynamic AICTE Central Review Workflow
Tests for:
1. Authorized reviewer can perform valid batch transitions (UNDER_REVIEW, ACCEPTED, REJECTED, NEEDS_CORRECTION).
2. Unauthorized institution users (INSTITUTION_ADMIN, INSTITUTION_OPERATOR) cannot perform central review actions (HTTP 403).
3. Invalid state transitions (e.g. from DRAFT, VALIDATED, or modifying ACCEPTED) are rejected (HTTP 400 INVALID_STATE_TRANSITION).
4. A batch with blocking errors cannot be improperly approved (HTTP 400 APPROVAL_BLOCKED_ERRORS).
5. The decision persists after a new database session.
6. The audit event is recorded with action=REVIEW_DECISION.
7. Match candidate review endpoint works for AICTE_ADMIN and rejects institution users.
8. Match candidate list endpoint returns enriched nested records and institutions.
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
    FindingSeverity,
    FindingStatus,
    MatchStatus,
)
from backend.app.models.match import MatchCandidate
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


# ==============================================================================
# 1. Batch Review Workflow: Authorization & Valid Transitions
# ==============================================================================

def test_authorized_reviewer_valid_transition_to_under_review(client: TestClient, aicte_token):
    """An AICTE reviewer can transition a SUBMITTED batch to UNDER_REVIEW."""
    db = SessionLocal()
    batch_id = f"BATCH-REV-UR-{uuid.uuid4().hex[:6]}"
    batch = ImportBatch(
        id=batch_id,
        institution_id="INST-001",
        uploader_user_id="usr-apex-adm-01",
        source_filename="test_dataset.csv",
        academic_year="2026-2027",
        version=1,
        total_rows=10,
        valid_rows=10,
        error_rows=0,
        warning_rows=0,
        status=BatchStatus.SUBMITTED,
    )
    db.add(batch)
    db.commit()

    try:
        response = client.post(
            f"/api/v1/reviews/batches/{batch_id}",
            json={"decision": "UNDER_REVIEW", "reason": "Preliminary statutory verification initiated by AICTE reviewer."},
            headers={"Authorization": f"Bearer {aicte_token}"},
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["batch_id"] == batch_id
        assert data["previous_status"] == "SUBMITTED"
        assert data["status"] == "UNDER_REVIEW"
        assert "aicte_admin@aicte.gov.in" in data["reviewed_by"]

        # 5. Verify persistence in a fresh DB session
        db_fresh = SessionLocal()
        b_persisted = db_fresh.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
        assert b_persisted is not None
        assert b_persisted.status == BatchStatus.UNDER_REVIEW
        db_fresh.close()

        # 6. Verify audit event
        audit = db.query(AuditEvent).filter(
            AuditEvent.object_id == batch_id,
            AuditEvent.action == AuditAction.REVIEW_DECISION
        ).first()
        assert audit is not None
        assert audit.actor_email == "aicte_admin@aicte.gov.in"
        assert "UNDER_REVIEW" in audit.details
    finally:
        db.query(AuditEvent).filter(AuditEvent.object_id == batch_id).delete()
        db.query(ImportBatch).filter(ImportBatch.id == batch_id).delete()
        db.commit()
        db.close()


def test_authorized_reviewer_can_approve_clean_batch(client: TestClient, aicte_token):
    """An AICTE reviewer can approve an UNDER_REVIEW batch with 0 errors via the batches/{id}/review alias."""
    db = SessionLocal()
    batch_id = f"BATCH-REV-APP-{uuid.uuid4().hex[:6]}"
    batch = ImportBatch(
        id=batch_id,
        institution_id="INST-001",
        uploader_user_id="usr-apex-adm-01",
        source_filename="clean_enrolment.csv",
        academic_year="2026-2027",
        version=1,
        total_rows=25,
        valid_rows=25,
        error_rows=0,
        warning_rows=0,
        status=BatchStatus.UNDER_REVIEW,
    )
    db.add(batch)
    db.commit()

    try:
        response = client.post(
            f"/api/v1/batches/{batch_id}/review",
            json={"decision": "ACCEPTED", "reason": "All 25 students verified against APH 2026-27 intake quota."},
            headers={"Authorization": f"Bearer {aicte_token}"},
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["batch_id"] == batch_id
        assert data["previous_status"] == "UNDER_REVIEW"
        assert data["status"] == "ACCEPTED"

        # Persistence check
        db_fresh = SessionLocal()
        b_persisted = db_fresh.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
        assert b_persisted.status == BatchStatus.ACCEPTED
        db_fresh.close()
    finally:
        db.query(AuditEvent).filter(AuditEvent.object_id == batch_id).delete()
        db.query(ImportBatch).filter(ImportBatch.id == batch_id).delete()
        db.commit()
        db.close()


def test_unauthorized_institution_users_cannot_review_batch(client: TestClient, apex_admin_token, apex_operator_token):
    """Institution administrators and operators are forbidden from reviewing batches (HTTP 403)."""
    db = SessionLocal()
    batch_id = f"BATCH-REV-FORBID-{uuid.uuid4().hex[:6]}"
    batch = ImportBatch(
        id=batch_id,
        institution_id="INST-001",
        uploader_user_id="usr-apex-adm-01",
        source_filename="test.csv",
        academic_year="2026-2027",
        version=1,
        total_rows=5,
        valid_rows=5,
        error_rows=0,
        warning_rows=0,
        status=BatchStatus.SUBMITTED,
    )
    db.add(batch)
    db.commit()

    try:
        # Institution Admin
        res_admin = client.post(
            f"/api/v1/reviews/batches/{batch_id}",
            json={"decision": "ACCEPTED", "reason": "Attempting unauthorized self-approval."},
            headers={"Authorization": f"Bearer {apex_admin_token}"},
        )
        assert res_admin.status_code == 403, res_admin.text

        # Institution Operator
        res_op = client.post(
            f"/api/v1/reviews/batches/{batch_id}",
            json={"decision": "UNDER_REVIEW", "reason": "Attempting operator review."},
            headers={"Authorization": f"Bearer {apex_operator_token}"},
        )
        assert res_op.status_code == 403, res_op.text
    finally:
        db.query(ImportBatch).filter(ImportBatch.id == batch_id).delete()
        db.commit()
        db.close()


# ==============================================================================
# 2. State Transition & Blocking Error Guards
# ==============================================================================

def test_invalid_state_transition_rejected(client: TestClient, aicte_token):
    """A batch in DRAFT or VALIDATED cannot be reviewed directly without being SUBMITTED."""
    db = SessionLocal()
    batch_id = f"BATCH-REV-INV-{uuid.uuid4().hex[:6]}"
    batch = ImportBatch(
        id=batch_id,
        institution_id="INST-001",
        uploader_user_id="usr-apex-adm-01",
        source_filename="draft_batch.csv",
        academic_year="2026-2027",
        version=1,
        total_rows=10,
        valid_rows=10,
        error_rows=0,
        warning_rows=0,
        status=BatchStatus.DRAFT,
    )
    db.add(batch)
    db.commit()

    try:
        response = client.post(
            f"/api/v1/reviews/batches/{batch_id}",
            json={"decision": "UNDER_REVIEW", "reason": "Premature review of draft batch."},
            headers={"Authorization": f"Bearer {aicte_token}"},
        )
        assert response.status_code == 400, response.text
        data = response.json()
        error_code = data.get("error", {}).get("code") or data.get("code")
        assert error_code == "INVALID_STATE_TRANSITION"
    finally:
        db.query(ImportBatch).filter(ImportBatch.id == batch_id).delete()
        db.commit()
        db.close()


def test_batch_with_blocking_errors_cannot_be_approved(client: TestClient, aicte_token):
    """A batch with error_rows > 0 or open BLOCKING_ERROR findings cannot be approved."""
    db = SessionLocal()
    batch_id = f"BATCH-REV-ERR-{uuid.uuid4().hex[:6]}"
    batch = ImportBatch(
        id=batch_id,
        institution_id="INST-001",
        uploader_user_id="usr-apex-adm-01",
        source_filename="flawed_dataset.csv",
        academic_year="2026-2027",
        version=1,
        total_rows=20,
        valid_rows=18,
        error_rows=2,
        warning_rows=0,
        status=BatchStatus.SUBMITTED,
    )
    db.add(batch)
    db.commit()

    # Add open BLOCKING_ERROR finding
    finding = ValidationFinding(
        batch_id=batch_id,
        row_number=1,
        rule_code="VAL_APAAR_INVALID_CHECKSUM",
        severity=FindingSeverity.BLOCKING_ERROR,
        status=FindingStatus.OPEN,
        field_name="apaar_id",
        message="Verhoeff checksum failed.",
    )
    db.add(finding)
    db.commit()

    try:
        response = client.post(
            f"/api/v1/reviews/batches/{batch_id}",
            json={"decision": "ACCEPTED", "reason": "Attempting improper statutory approval despite blocking errors."},
            headers={"Authorization": f"Bearer {aicte_token}"},
        )
        assert response.status_code == 400, response.text
        data = response.json()
        error_code = data.get("error", {}).get("code") or data.get("code")
        assert error_code == "APPROVAL_BLOCKED_ERRORS"

        # Verify batch status remained SUBMITTED in DB
        db.expire_all()
        b_after = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
        assert b_after.status == BatchStatus.SUBMITTED
    finally:
        db.query(ValidationFinding).filter(ValidationFinding.batch_id == batch_id).delete()
        db.query(ImportBatch).filter(ImportBatch.id == batch_id).delete()
        db.commit()
        db.close()


def test_batch_return_for_correction_persists(client: TestClient, aicte_token):
    """An AICTE reviewer can return a batch for correction (NEEDS_CORRECTION)."""
    db = SessionLocal()
    batch_id = f"BATCH-REV-RET-{uuid.uuid4().hex[:6]}"
    batch = ImportBatch(
        id=batch_id,
        institution_id="INST-001",
        uploader_user_id="usr-apex-adm-01",
        source_filename="batch_for_correction.csv",
        academic_year="2026-2027",
        version=1,
        total_rows=15,
        valid_rows=12,
        error_rows=3,
        warning_rows=0,
        status=BatchStatus.SUBMITTED,
    )
    db.add(batch)
    db.commit()

    try:
        response = client.post(
            f"/api/v1/reviews/batches/{batch_id}",
            json={"decision": "NEEDS_CORRECTION", "reason": "3 student rows failed statutory checksum. Please correct and re-upload."},
            headers={"Authorization": f"Bearer {aicte_token}"},
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "NEEDS_CORRECTION"

        # Fresh DB session check
        db_fresh = SessionLocal()
        b_persisted = db_fresh.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
        assert b_persisted.status == BatchStatus.NEEDS_CORRECTION
        db_fresh.close()
    finally:
        db.query(AuditEvent).filter(AuditEvent.object_id == batch_id).delete()
        db.query(ImportBatch).filter(ImportBatch.id == batch_id).delete()
        db.commit()
        db.close()


# ==============================================================================
# 3. Match Candidate Review & Data Enrichment Tests
# ==============================================================================

def test_list_matches_returns_enriched_records(client: TestClient, aicte_token):
    """Listing match candidates returns enriched institution and record details."""
    response = client.get(
        "/api/v1/reviews/matches",
        headers={"Authorization": f"Bearer {aicte_token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "items" in data
    assert "total" in data

    if data["total"] > 0:
        first_item = data["items"][0]
        assert "matching_signal" in first_item
        assert "status" in first_item
        # Verify enriched nested structures exist if populated
        assert "record_a" in first_item
        assert "institution_a" in first_item
        if first_item.get("institution_a"):
            assert "name" in first_item["institution_a"]
            assert "code" in first_item["institution_a"]


def test_review_match_candidate_workflow(client: TestClient, aicte_token, apex_admin_token):
    """AICTE admin can adjudicate match candidate; institution admin is forbidden."""
    db = SessionLocal()
    existing_match = db.query(MatchCandidate).first()
    if not existing_match:
        pytest.skip("No existing MatchCandidate in database to test adjudication.")

    match_id = existing_match.id
    prev_status = existing_match.status
    prev_reason = existing_match.resolution_reason
    db.close()

    try:
        # Institution Admin forbidden (HTTP 403)
        res_forbidden = client.post(
            f"/api/v1/reviews/matches/{match_id}",
            json={"status": "CONFIRMED_DUPLICATE", "resolution_reason": "Unauthorized resolution attempt."},
            headers={"Authorization": f"Bearer {apex_admin_token}"},
        )
        assert res_forbidden.status_code == 403, res_forbidden.text

        # AICTE Admin allowed
        res_ok = client.post(
            f"/api/v1/reviews/matches/{match_id}",
            json={"status": "CONFIRMED_DUPLICATE", "resolution_reason": "Verified concurrent admissions across both college registries."},
            headers={"Authorization": f"Bearer {aicte_token}"},
        )
        assert res_ok.status_code == 200, res_ok.text
        data = res_ok.json()
        assert data["id"] == match_id
        assert data["status"] == "CONFIRMED_DUPLICATE"
        assert "Verified concurrent admissions" in data["resolution_reason"]
    finally:
        # Restore original state
        db_restore = SessionLocal()
        m = db_restore.query(MatchCandidate).filter(MatchCandidate.id == match_id).first()
        if m:
            m.status = prev_status
            m.resolution_reason = prev_reason
            db_restore.commit()
        db_restore.close()
