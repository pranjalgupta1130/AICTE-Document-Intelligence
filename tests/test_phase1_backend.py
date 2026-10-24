import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.seed.seed_data import seed_database
from backend.app.db.session import SessionLocal
from backend.app.models.audit import AuditEvent
from backend.app.models.enums import AuditAction

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

# --------------------------------------------------------------------------
# 1. Health Check & System Readiness
# --------------------------------------------------------------------------
def test_root_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "version" in data
    assert "service" in data

def test_api_v1_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

# --------------------------------------------------------------------------
# 2. Authentication Flow (FR-01)
# --------------------------------------------------------------------------
def test_login_aicte_admin_success(client):
    response = client.post("/api/v1/auth/login", json={
        "email": "aicte_admin@aicte.gov.in",
        "password": "DemoPassword@2026"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == "AICTE_ADMIN"
    assert data["user"]["institution_id"] is None

def test_login_institution_admin_success(client):
    response = client.post("/api/v1/auth/login", json={
        "email": "apex_admin@apex.edu.in",
        "password": "DemoPassword@2026"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["role"] == "INSTITUTION_ADMIN"
    assert data["user"]["institution_id"] == "INST-001"
    assert data["user"]["institution_name"] == "Apex Institute of Technology"

def test_login_institution_operator_success(client):
    response = client.post("/api/v1/auth/login", json={
        "email": "apex_operator@apex.edu.in",
        "password": "DemoPassword@2026"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["role"] == "INSTITUTION_OPERATOR"
    assert data["user"]["institution_id"] == "INST-001"

def test_login_invalid_password(client):
    response = client.post("/api/v1/auth/login", json={
        "email": "apex_admin@apex.edu.in",
        "password": "WrongPassword123!"
    })
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "AUTHENTICATION_FAILED"
    assert "request_id" in data["error"]

def test_login_nonexistent_user(client):
    response = client.post("/api/v1/auth/login", json={
        "email": "nobody@doesnotexist.edu",
        "password": "AnyPassword"
    })
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "AUTHENTICATION_FAILED"

# --------------------------------------------------------------------------
# 3. Session & Current User Profile
# --------------------------------------------------------------------------
def test_get_current_user_me(client):
    token = get_auth_token(client, "apex_admin@apex.edu.in")
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "apex_admin@apex.edu.in"
    assert data["role"] == "INSTITUTION_ADMIN"
    assert data["institution_id"] == "INST-001"

def test_get_current_user_unauthorized(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "AUTHENTICATION_REQUIRED"

def test_get_current_user_invalid_token(client):
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.jwt.token"})
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "AUTHENTICATION_FAILED"

# --------------------------------------------------------------------------
# 4. Server-Side RBAC & Institution Isolation (FR-01, FR-02, NFR-01)
# --------------------------------------------------------------------------
def test_aicte_admin_lists_all_institutions(client):
    token = get_auth_token(client, "aicte_admin@aicte.gov.in")
    response = client.get("/api/v1/institutions", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    ids = [inst["id"] for inst in data["items"]]
    assert "INST-001" in ids
    assert "INST-002" in ids
    assert "INST-003" in ids

def test_institution_admin_strictly_isolated_to_own_institution(client):
    token = get_auth_token(client, "apex_admin@apex.edu.in")
    response = client.get("/api/v1/institutions", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    # Apex admin should only see their own institution
    assert data["total"] == 1
    assert data["items"][0]["id"] == "INST-001"
    assert data["items"][0]["name"] == "Apex Institute of Technology"

def test_institution_operator_strictly_isolated_to_own_institution(client):
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    response = client.get("/api/v1/institutions", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == "INST-001"

def test_apex_admin_reads_own_intake(client):
    token = get_auth_token(client, "apex_admin@apex.edu.in")
    response = client.get("/api/v1/intake", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    # Every returned intake item MUST belong to INST-001
    for item in data["items"]:
        assert item["institution_id"] == "INST-001"
        assert item["total_approved_intake"] == item["regular_intake"] + item["supernumerary_intake"]

def test_apex_admin_cannot_access_other_institution_intake(client):
    token = get_auth_token(client, "apex_admin@apex.edu.in")
    # Apex (INST-001) attempts to query Bharat (INST-002) intake
    response = client.get("/api/v1/intake?institution_id=INST-002", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "INSTITUTION_SCOPE_VIOLATION"

def test_apex_operator_cannot_access_other_institution_intake(client):
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    response = client.get("/api/v1/intake?institution_id=INST-002", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "INSTITUTION_SCOPE_VIOLATION"

def test_aicte_admin_can_access_specific_institution_intake(client):
    token = get_auth_token(client, "aicte_admin@aicte.gov.in")
    response = client.get("/api/v1/intake?institution_id=INST-002", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    for item in data["items"]:
        assert item["institution_id"] == "INST-002"

def test_aicte_admin_can_access_all_intakes(client):
    token = get_auth_token(client, "aicte_admin@aicte.gov.in")
    response = client.get("/api/v1/intake", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    inst_ids = {item["institution_id"] for item in data["items"]}
    assert "INST-001" in inst_ids
    assert "INST-002" in inst_ids
    assert "INST-003" in inst_ids

# --------------------------------------------------------------------------
# 5. Audit Logging Verification (FR-13)
# --------------------------------------------------------------------------
def test_audit_log_captures_login_events(client):
    # Perform a login
    client.post("/api/v1/auth/login", json={
        "email": "bharat_admin@bharat.edu.in",
        "password": "DemoPassword@2026"
    })

    db = SessionLocal()
    try:
        event = db.query(AuditEvent).filter(
            AuditEvent.actor_email == "bharat_admin@bharat.edu.in",
            AuditEvent.action == AuditAction.LOGIN,
            AuditEvent.outcome == "SUCCESS"
        ).order_by(AuditEvent.timestamp.desc()).first()

        assert event is not None
        assert event.actor_role == "INSTITUTION_ADMIN"
        assert event.institution_id == "INST-002"
        assert event.timestamp is not None
    finally:
        db.close()

# --------------------------------------------------------------------------
# 6. Request ID and Standard Error Response Shape
# --------------------------------------------------------------------------
def test_request_id_middleware(client):
    response = client.get("/health", headers={"X-Request-ID": "test-req-custom-999"})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "test-req-custom-999"

def test_validation_error_shape(client):
    # Malformed body missing required field
    response = client.post("/api/v1/auth/login", json={"email": "apex_admin@apex.edu.in"})
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "request_id" in data["error"]

# --------------------------------------------------------------------------
# 7. Audit Findings Regression Tests (AUDIT-01 to AUDIT-07)
# --------------------------------------------------------------------------
def test_audit_01_direct_get_me_route_alias(client):
    """AUDIT-01: Verify GET /api/v1/me route alias matches Brief Section 9."""
    token = get_auth_token(client, "apex_admin@apex.edu.in")
    response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "apex_admin@apex.edu.in"
    assert data["role"] == "INSTITUTION_ADMIN"
    assert data["institution_id"] == "INST-001"

def test_audit_02_institution_user_lifecycle_semantics():
    """AUDIT-02: Disassociating user preserves user; deleting institution preserves user."""
    from backend.app.models.institution import Institution
    from backend.app.models.user import User
    from backend.app.models.enums import UserRole
    from backend.app.core.security import hash_password
    import uuid

    db = SessionLocal()
    try:
        test_inst_id = f"INST-TEST-{uuid.uuid4().hex[:6]}"
        test_inst = Institution(
            id=test_inst_id,
            name="Temporary Test College",
            code=f"TMP-{uuid.uuid4().hex[:4]}",
            state="Goa",
            status="ACTIVE"
        )
        db.add(test_inst)
        db.commit()

        test_user_id = f"usr-test-{uuid.uuid4().hex[:6]}"
        test_user = User(
            id=test_user_id,
            email=f"temp_{uuid.uuid4().hex[:6]}@college.edu",
            hashed_password=hash_password("DemoPassword@2026"),
            full_name="Temporary Faculty",
            role=UserRole.INSTITUTION_OPERATOR,
            institution_id=test_inst_id,
            is_active=True
        )
        db.add(test_user)
        db.commit()

        # Test 1: Disassociate user from institution
        test_user.institution_id = None
        db.commit()
        db.refresh(test_user)
        assert test_user.institution_id is None
        reloaded_user = db.query(User).filter(User.id == test_user_id).first()
        assert reloaded_user is not None

        # Re-associate and delete institution
        test_user.institution_id = test_inst_id
        db.commit()

        # Delete institution
        db.delete(test_inst)
        db.commit()

        # User must still exist in DB without cascading deletion
        persisted_user = db.query(User).filter(User.id == test_user_id).first()
        assert persisted_user is not None
        # Clean up
        db.delete(persisted_user)
        db.commit()
    finally:
        db.close()

def test_audit_03_deactivated_account_login_audited(client):
    """AUDIT-03: Deactivated account with valid password raises 401 and persists AuditEvent with outcome=BLOCKED."""
    from backend.app.models.user import User
    from backend.app.models.enums import UserRole
    from backend.app.core.security import hash_password
    import uuid

    deact_email = f"deactivated_{uuid.uuid4().hex[:6]}@college.edu"
    pwd = "DemoPassword@2026"
    db = SessionLocal()
    try:
        deact_user = User(
            id=f"usr-deact-{uuid.uuid4().hex[:6]}",
            email=deact_email,
            hashed_password=hash_password(pwd),
            full_name="Deactivated Staff",
            role=UserRole.INSTITUTION_OPERATOR,
            institution_id="INST-001",
            is_active=False
        )
        db.add(deact_user)
        db.commit()

        response = client.post("/api/v1/auth/login", json={
            "email": deact_email,
            "password": pwd
        })
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"
        assert "deactivated" in response.json()["error"]["message"].lower()

        # Verify audit event was committed with BLOCKED outcome
        event = db.query(AuditEvent).filter(
            AuditEvent.actor_email == deact_email,
            AuditEvent.action == AuditAction.LOGIN,
            AuditEvent.outcome == "BLOCKED"
        ).order_by(AuditEvent.timestamp.desc()).first()
        assert event is not None
        assert "deactivated" in event.details.lower()
    finally:
        db.close()

def test_audit_04_approved_intake_compound_uniqueness():
    """AUDIT-04: Inserting duplicate intake for same institution+programme+year raises IntegrityError."""
    from backend.app.models.institution import ApprovedIntake
    from sqlalchemy.exc import IntegrityError
    import uuid

    db = SessionLocal()
    try:
        intake_1 = ApprovedIntake(
            id=f"INTAKE-DUP-1-{uuid.uuid4().hex[:6]}",
            institution_id="INST-001",
            programme_id="PROG-001-CSE",
            academic_year="2029-2030",
            regular_intake=60,
            supernumerary_intake=6
        )
        db.add(intake_1)
        db.commit()

        intake_2 = ApprovedIntake(
            id=f"INTAKE-DUP-2-{uuid.uuid4().hex[:6]}",
            institution_id="INST-001",
            programme_id="PROG-001-CSE",
            academic_year="2029-2030",  # Duplicate compound key
            regular_intake=120,
            supernumerary_intake=12
        )
        db.add(intake_2)
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()

def test_audit_05_seed_database_rollback_on_failure(monkeypatch):
    """AUDIT-05: Seeding rollback on failure and re-raise exception."""
    from backend.app.seed.seed_data import seed_database
    from sqlalchemy.orm import Session

    def failing_commit(self):
        raise RuntimeError("Simulated DB commit error during seeding")

    monkeypatch.setattr(Session, "commit", failing_commit)

    with pytest.raises(RuntimeError, match="Simulated DB commit error during seeding"):
        seed_database(reset=False)

def test_audit_06_expired_jwt_token_rejection(client):
    """AUDIT-06: Expired JWT token is rejected with 401 AUTHENTICATION_FAILED and expired message."""
    from datetime import timedelta
    from backend.app.core.security import create_access_token

    expired_token = create_access_token(
        subject="apex_admin@apex.edu.in",
        role="INSTITUTION_ADMIN",
        institution_id="INST-001",
        expires_delta=timedelta(seconds=-10)
    )
    response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "AUTHENTICATION_FAILED"
    assert "expired" in data["error"]["message"].lower()

def test_audit_07_external_verifier_permission_denial(client):
    """AUDIT-07: External verifier role is forbidden from browsing institutions (403 PERMISSION_DENIED)."""
    from backend.app.models.user import User
    from backend.app.models.enums import UserRole
    from backend.app.core.security import hash_password
    import uuid

    db = SessionLocal()
    verifier_email = f"verifier_{uuid.uuid4().hex[:6]}@external.gov.in"
    try:
        verifier_user = User(
            id=f"usr-verif-{uuid.uuid4().hex[:6]}",
            email=verifier_email,
            hashed_password=hash_password("DemoPassword@2026"),
            full_name="External Evaluator",
            role=UserRole.EXTERNAL_VERIFIER,
            institution_id=None,
            is_active=True
        )
        db.add(verifier_user)
        db.commit()

        token = get_auth_token(client, verifier_email)
        response = client.get("/api/v1/institutions", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 403
        data = response.json()
        assert data["error"]["code"] == "PERMISSION_DENIED"
        assert "external verifier" in data["error"]["message"].lower()
    finally:
        db.close()


def test_audit_p2_01_secret_key_configuration_validation(client):
    """
    P2-01 Audit Remediation Test:
    - Production configuration rejects a missing / empty secret.
    - Production configuration rejects the insecure development default.
    - Production configuration rejects secrets shorter than 32 characters.
    - Production configuration accepts a sufficiently long secret (>= 32 chars).
    - Development and test configurations continue to behave as intended with dev secret.
    - Secrets are never leaked into exception messages.
    - Existing login and JWT issuance/verification remain intact.
    """
    from backend.app.core.config import Settings, INSECURE_DEFAULT_SECRET_KEY, MINIMUM_SECRET_KEY_LENGTH

    # 1. Production with missing / whitespace secret -> Rejects with RuntimeError
    s_missing = Settings(ENVIRONMENT="production", SECRET_KEY="")
    with pytest.raises(RuntimeError) as exc_info:
        s_missing.validate_security_configuration()
    assert "SECRET_KEY is not configured" in str(exc_info.value)
    assert INSECURE_DEFAULT_SECRET_KEY not in str(exc_info.value)

    # 2. Production with insecure default secret -> Rejects with RuntimeError
    s_default = Settings(ENVIRONMENT="production", SECRET_KEY=INSECURE_DEFAULT_SECRET_KEY)
    with pytest.raises(RuntimeError) as exc_info:
        s_default.validate_security_configuration()
    assert "insecure development default" in str(exc_info.value)
    assert INSECURE_DEFAULT_SECRET_KEY not in str(exc_info.value)

    # 3. Production with secret shorter than 32 characters -> Rejects with RuntimeError
    short_secret = "too-short-key-12345"
    s_short = Settings(ENVIRONMENT="production", SECRET_KEY=short_secret)
    with pytest.raises(RuntimeError) as exc_info:
        s_short.validate_security_configuration()
    assert f"at least {MINIMUM_SECRET_KEY_LENGTH} characters long" in str(exc_info.value)
    # Ensure raw secret is not leaked in exception string
    assert short_secret not in str(exc_info.value)

    # 4. Production with strong secret (>= 32 characters) -> Validates cleanly
    strong_secret = "c7d9e1f2a3b4c5d6e7f8a9b0c1d2e3f4g5h6i7j8k9l0m1n2o3p4q5r6s7t8u9v0"
    s_valid = Settings(ENVIRONMENT="production", SECRET_KEY=strong_secret)
    s_valid.validate_security_configuration()  # Must not raise

    # 5. Development and test environment -> Accepts dev secret without error
    s_dev = Settings(ENVIRONMENT="development", SECRET_KEY=INSECURE_DEFAULT_SECRET_KEY)
    s_dev.validate_security_configuration()  # Must not raise

    s_test = Settings(ENVIRONMENT="test", SECRET_KEY=INSECURE_DEFAULT_SECRET_KEY)
    s_test.validate_security_configuration()  # Must not raise

    # 6. Verify existing login and JWT validation behavior remains intact
    response = client.post("/api/v1/auth/login", json={
        "email": "apex_admin@apex.edu.in",
        "password": "DemoPassword@2026"
    })
    assert response.status_code == 200
    token = response.json()["access_token"]
    assert token is not None

    me_res = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "apex_admin@apex.edu.in"
