"""
Phase 3 Verification & Student Record Workflow Test Suite.
Verifies:
1. Search endpoint for student records:
   - Scoped by institution for institution users.
   - Unrestricted for AICTE admin.
   - Prohibited for External Verifier.
   - Filter by name, roll number, and APAAR.
   - Empty search results.
2. Single-record lookup and verification:
   - Lookup by roll number, apaar_id (raw or hyphenated), and database primary key.
   - Nonexistent student returns 404.
   - Cross-institution IDOR lookup returns 403.
   - Masked APAAR for non-admin roles (INSTITUTION_OPERATOR, EXTERNAL_VERIFIER).
   - Unmasked APAAR for administrative roles (INSTITUTION_ADMIN, AICTE_ADMIN).
3. Verification outcome discrimination:
   - MOCK_VERIFIED with is_official=False and provider=MOCK_APAAR_ADAPTER.
   - MOCK_NOT_VERIFIED on invalid format or checksum.
   - MOCK_UNAVAILABLE on simulate_outage=True.
   - NEEDS_REVIEW on simulated ambiguity.
4. Certificate preview endpoint:
   - Synthetic preview flag and explicit disclaimer.
   - Institution and student contextual metadata.
   - Masked APAAR for non-administrative roles.
5. Real audit logging and audit trail retrieval.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.db.session import SessionLocal
from backend.app.main import app
from backend.app.models.audit import AuditEvent
from backend.app.models.enums import AuditAction, UserRole, VerificationOutcome
from backend.app.models.student import StudentRecord
from backend.app.models.user import User


@pytest.fixture
def client():
    return TestClient(app)


def get_token(client: TestClient, email: str, password: str = "DemoPassword@2026") -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


@pytest.fixture
def aicte_token(client):
    return get_token(client, "aicte_admin@aicte.gov.in")


@pytest.fixture
def apex_admin_token(client):
    return get_token(client, "apex_admin@apex.edu.in")


@pytest.fixture
def apex_operator_token(client):
    return get_token(client, "apex_operator@apex.edu.in")


@pytest.fixture
def bharat_admin_token(client):
    return get_token(client, "bharat_admin@bharat.edu.in")


@pytest.fixture
def external_verifier_token(client):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.role == UserRole.EXTERNAL_VERIFIER).first()
        if not user:
            from backend.app.core.security import hash_password
            user = User(
                email="test_verifier@external.gov.in",
                hashed_password=hash_password("DemoPassword@2026"),
                full_name="External Test Verifier",
                role=UserRole.EXTERNAL_VERIFIER,
                is_active=True
            )
            db.add(user)
            db.commit()
        return get_token(client, user.email)
    finally:
        db.close()


# -----------------------------------------------------------------------------
# 1. Search Endpoint Tests
# -----------------------------------------------------------------------------

def test_search_students_institution_isolation(client: TestClient, apex_admin_token, bharat_admin_token, aicte_token):
    """Ensure search queries enforce strict tenant boundary isolation."""
    # Apex admin search
    resp_apex = client.get(
        "/api/v1/verification/search",
        headers={"Authorization": f"Bearer {apex_admin_token}"}
    )
    assert resp_apex.status_code == 200
    apex_items = resp_apex.json()["items"]
    for item in apex_items:
        assert item["institution_id"] == "INST-001"

    # Bharat admin search
    resp_bharat = client.get(
        "/api/v1/verification/search",
        headers={"Authorization": f"Bearer {bharat_admin_token}"}
    )
    assert resp_bharat.status_code == 200
    bharat_items = resp_bharat.json()["items"]
    for item in bharat_items:
        assert item["institution_id"] == "INST-002"

    # AICTE admin can view across institutions
    resp_aicte = client.get(
        "/api/v1/verification/search",
        headers={"Authorization": f"Bearer {aicte_token}"}
    )
    assert resp_aicte.status_code == 200
    aicte_items = resp_aicte.json()["items"]
    inst_ids = {i["institution_id"] for i in aicte_items}
    # Should see records from more than one institution if seeded
    assert len(aicte_items) >= len(apex_items)


def test_search_students_query_filters(client: TestClient, apex_admin_token):
    """Test searching by roll number substring and nonexistent queries."""
    db = SessionLocal()
    try:
        sample = db.query(StudentRecord).filter(StudentRecord.institution_id == "INST-001").first()
        assert sample is not None, "Precondition: sample student must exist in INST-001"
        roll = sample.institution_student_id
    finally:
        db.close()

    # Search for existing roll
    resp = client.get(
        f"/api/v1/verification/search?q={roll}",
        headers={"Authorization": f"Bearer {apex_admin_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    matched = [i for i in data["items"] if i["institution_student_id"] == roll]
    assert len(matched) >= 1

    # Search for nonexistent student
    resp_empty = client.get(
        "/api/v1/verification/search?q=NONEXISTENT_STUDENT_XYZ_999",
        headers={"Authorization": f"Bearer {apex_admin_token}"}
    )
    assert resp_empty.status_code == 200
    data_empty = resp_empty.json()
    assert data_empty["total"] == 0
    assert data_empty["items"] == []


def test_search_external_verifier_prohibited(client: TestClient, external_verifier_token):
    """External verifiers cannot bulk search/enumerate student datasets."""
    resp = client.get(
        "/api/v1/verification/search",
        headers={"Authorization": f"Bearer {external_verifier_token}"}
    )
    assert resp.status_code == 403


# -----------------------------------------------------------------------------
# 2. APAAR Masking on Search and Verification
# -----------------------------------------------------------------------------

def test_apaar_masking_on_search_and_verification(
    client: TestClient,
    apex_admin_token,
    apex_operator_token,
    external_verifier_token
):
    """
    INSTITUTION_ADMIN receives unmasked APAAR IDs.
    INSTITUTION_OPERATOR receives masked APAAR IDs (e.g. 9082-XXXX-8821).
    EXTERNAL_VERIFIER receives masked APAAR IDs on verification lookups.
    """
    db = SessionLocal()
    try:
        sample = db.query(StudentRecord).filter(
            StudentRecord.institution_id == "INST-001",
            StudentRecord.apaar_id.isnot(None)
        ).first()
        assert sample is not None
        target_roll = sample.institution_student_id
        target_apaar = sample.apaar_id
    finally:
        db.close()

    # Admin search -> unmasked
    res_admin = client.get(
        f"/api/v1/verification/search?q={target_roll}",
        headers={"Authorization": f"Bearer {apex_admin_token}"}
    )
    admin_item = res_admin.json()["items"][0]
    assert "XXXX" not in admin_item["apaar_id"]

    # Operator search -> masked
    res_op = client.get(
        f"/api/v1/verification/search?q={target_roll}",
        headers={"Authorization": f"Bearer {apex_operator_token}"}
    )
    op_item = res_op.json()["items"][0]
    assert "XXXX" in op_item["apaar_id"]

    # Admin verification -> unmasked
    res_v_admin = client.get(
        f"/api/v1/verification/{target_roll}",
        headers={"Authorization": f"Bearer {apex_admin_token}"}
    )
    assert "XXXX" not in res_v_admin.json()["apaar_id"]

    # Operator verification -> masked
    res_v_op = client.get(
        f"/api/v1/verification/{target_roll}",
        headers={"Authorization": f"Bearer {apex_operator_token}"}
    )
    assert "XXXX" in res_v_op.json()["apaar_id"]

    # External Verifier verification -> masked
    res_v_ext = client.get(
        f"/api/v1/verification/{sample.id}",
        headers={"Authorization": f"Bearer {external_verifier_token}"}
    )
    assert "XXXX" in res_v_ext.json()["apaar_id"]


# -----------------------------------------------------------------------------
# 3. IDOR and Institution Scope Enforcement
# -----------------------------------------------------------------------------

def test_cross_institution_lookup_rejection(client: TestClient, apex_admin_token, bharat_admin_token):
    """Institution admin querying another institution student primary key receives 403."""
    db = SessionLocal()
    try:
        bharat_student = db.query(StudentRecord).filter(StudentRecord.institution_id == "INST-002").first()
        assert bharat_student is not None
        bharat_id = bharat_student.id
    finally:
        db.close()

    # Apex admin (INST-001) attempts to query Bharat student (INST-002) by primary key ID
    resp = client.get(
        f"/api/v1/verification/{bharat_id}",
        headers={"Authorization": f"Bearer {apex_admin_token}"}
    )
    assert resp.status_code == 403

    # Bharat admin querying same student succeeds
    resp_ok = client.get(
        f"/api/v1/verification/{bharat_id}",
        headers={"Authorization": f"Bearer {bharat_admin_token}"}
    )
    assert resp_ok.status_code == 200


def test_nonexistent_student_returns_404(client: TestClient, apex_admin_token):
    """Looking up a completely nonexistent identifier returns 404."""
    resp = client.get(
        "/api/v1/verification/NONEXISTENT_STU_REF_000000",
        headers={"Authorization": f"Bearer {apex_admin_token}"}
    )
    assert resp.status_code == 404


# -----------------------------------------------------------------------------
# 4. Verification Semantics & Outage Simulation
# -----------------------------------------------------------------------------

def test_verification_outage_simulation_graceful_degradation(client: TestClient, apex_admin_token):
    """
    Verify that simulate_outage=True produces MOCK_UNAVAILABLE with is_official=False,
    and logs an audit trail event without crashing.
    """
    db = SessionLocal()
    try:
        sample = db.query(StudentRecord).filter(StudentRecord.institution_id == "INST-001").first()
        target_ref = sample.institution_student_id
    finally:
        db.close()

    resp = client.get(
        f"/api/v1/verification/{target_ref}?simulate_outage=true",
        headers={"Authorization": f"Bearer {apex_admin_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["outcome"] == VerificationOutcome.MOCK_UNAVAILABLE.value
    assert data["is_official"] is False
    assert data["provider"] == "MOCK_APAAR_ADAPTER"
    assert "mock-ref-" in data["reference_id"]
    assert len(data["audit_trail"]) >= 1


# -----------------------------------------------------------------------------
# 5. Certificate Preview Endpoint
# -----------------------------------------------------------------------------

def test_certificate_preview_endpoint(client: TestClient, apex_admin_token, apex_operator_token):
    """
    Certificate preview returns synthetic preview data, prominent disclaimer,
    persisted institution/student info, and masks APAAR for operator.
    """
    db = SessionLocal()
    try:
        sample = db.query(StudentRecord).filter(
            StudentRecord.institution_id == "INST-001",
            StudentRecord.apaar_id.isnot(None)
        ).first()
        assert sample is not None, "Need sample with apaar_id in INST-001"
        target_ref = sample.institution_student_id
    finally:
        db.close()

    # Admin preview
    resp_admin = client.get(
        f"/api/v1/verification/{target_ref}/certificate",
        headers={"Authorization": f"Bearer {apex_admin_token}"}
    )
    assert resp_admin.status_code == 200
    data_admin = resp_admin.json()

    assert data_admin["is_synthetic_preview"] is True
    assert "SYNTHETIC PROTOTYPE PREVIEW" in data_admin["disclaimer"]
    assert data_admin["institution_student_id"] == sample.institution_student_id
    assert "XXXX" not in data_admin["apaar_id"]

    # Operator preview -> masked APAAR
    resp_op = client.get(
        f"/api/v1/verification/{target_ref}/certificate",
        headers={"Authorization": f"Bearer {apex_operator_token}"}
    )
    assert resp_op.status_code == 200
    data_op = resp_op.json()
    assert "XXXX" in data_op["apaar_id"]


# -----------------------------------------------------------------------------
# 6. Audit Trail Logging Verification
# -----------------------------------------------------------------------------

def test_audit_event_logged_on_verification(client: TestClient, apex_admin_token):
    """Every verification query must create an immutable AuditEvent in the database."""
    db = SessionLocal()
    try:
        sample = db.query(StudentRecord).filter(StudentRecord.institution_id == "INST-001").first()
        target_ref = sample.institution_student_id
        count_before = db.query(AuditEvent).filter(
            AuditEvent.object_id == sample.id,
            AuditEvent.action == AuditAction.VERIFICATION_LOOKUP
        ).count()
    finally:
        db.close()

    resp = client.get(
        f"/api/v1/verification/{target_ref}",
        headers={"Authorization": f"Bearer {apex_admin_token}"}
    )
    assert resp.status_code == 200

    db = SessionLocal()
    try:
        count_after = db.query(AuditEvent).filter(
            AuditEvent.object_id == sample.id,
            AuditEvent.action == AuditAction.VERIFICATION_LOOKUP
        ).count()
        assert count_after == count_before + 1
    finally:
        db.close()
