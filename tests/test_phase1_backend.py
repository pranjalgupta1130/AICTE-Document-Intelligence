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
