import io
import json
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.seed.seed_data import seed_database
from backend.app.db.session import SessionLocal
from backend.app.models.audit import AuditEvent
from backend.app.models.batch import ImportBatch
from backend.app.models.enums import AuditAction, BatchStatus, FindingSeverity, MatchStatus, SeatType
from backend.app.models.institution import ApprovedIntake
from backend.app.models.match import MatchCandidate
from backend.app.models.student import StudentRecord
from backend.app.models.validation import ValidationFinding
from backend.app.services.validation_service import validate_verhoeff_checksum


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
# 1. Required Field & Syntax Validation Tests
# ==============================================================================
def test_validation_detects_missing_student_name(client):
    """Validation flags missing or short student name with RULE-REQ-001 (BLOCKING_ERROR)."""
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    csv_data = (
        "institution_student_id,student_name,programme_id,academic_year\n"
        "APEX-REQ-001,A,PROG-001-CSE,2026-2027\n"  # 1 char name (< 2 chars)
    )
    files = {"file": ("short_name.csv", csv_data, "text/csv")}
    import_res = client.post("/api/v1/imports", headers={"Authorization": f"Bearer {token}"}, files=files, data={"academic_year": "2026-2027"})
    assert import_res.status_code == 200
    batch_id = import_res.json()["batch_id"]

    val_res = client.post(f"/api/v1/batches/{batch_id}/validate", headers={"Authorization": f"Bearer {token}"})
    assert val_res.status_code == 200
    data = val_res.json()
    assert data["status"] == "NEEDS_CORRECTION"
    assert data["validation_summary"]["error_count"] >= 1

    findings_res = client.get(f"/api/v1/batches/{batch_id}/findings", headers={"Authorization": f"Bearer {token}"})
    findings = findings_res.json()["items"]
    rule_req_findings = [f for f in findings if f["rule_code"] == "RULE-REQ-001"]
    assert len(rule_req_findings) == 1
    assert rule_req_findings[0]["severity"] == "BLOCKING_ERROR"
    assert "at least 2 characters" in rule_req_findings[0]["message"]


def test_validation_detects_missing_and_invalid_apaar_syntax(client, monkeypatch):
    """Verify APAAR presence (WARNING by default) and format/checksum validation (BLOCKING_ERROR)."""
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    # 987654321012 has valid Verhoeff checksum.
    # 987654321019 has invalid Verhoeff checksum.
    # Row 1: Valid APAAR
    # Row 2: Missing APAAR (WARNING)
    # Row 3: Non-numeric / 10-digit APAAR (BLOCKING_ERROR)
    # Row 4: 12-digit invalid checksum (BLOCKING_ERROR)
    csv_data = (
        "institution_student_id,student_name,apaar_id,programme_id,academic_year\n"
        "APEX-AP-001,Student Valid,987654321012,PROG-001-CSE,2026-2027\n"
        "APEX-AP-002,Student Missing,,PROG-001-CSE,2026-2027\n"
        "APEX-AP-003,Student Short,1234567890,PROG-001-CSE,2026-2027\n"
        "APEX-AP-004,Student BadChecksum,987654321019,PROG-001-CSE,2026-2027\n"
    )
    files = {"file": ("apaar_tests.csv", csv_data, "text/csv")}
    import_res = client.post("/api/v1/imports", headers={"Authorization": f"Bearer {token}"}, files=files, data={"academic_year": "2026-2027"})
    batch_id = import_res.json()["batch_id"]

    val_res = client.post(f"/api/v1/batches/{batch_id}/validate", headers={"Authorization": f"Bearer {token}"})
    assert val_res.status_code == 200
    data = val_res.json()
    assert data["status"] == "NEEDS_CORRECTION"

    findings_res = client.get(f"/api/v1/batches/{batch_id}/findings", headers={"Authorization": f"Bearer {token}"})
    findings = findings_res.json()["items"]

    missing_apaar = [f for f in findings if f["rule_code"] == "RULE-APAAR-001"]
    assert len(missing_apaar) == 1
    assert missing_apaar[0]["severity"] == "WARNING"

    invalid_apaar = [f for f in findings if f["rule_code"] == "RULE-APAAR-002"]
    assert len(invalid_apaar) == 2  # Short length and bad checksum
    for f in invalid_apaar:
        assert f["severity"] == "BLOCKING_ERROR"


def test_validation_category_quota_mismatch(client):
    """Flag category inconsistencies (e.g. NRI student admitted under domestic quota) with WARNING."""
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    csv_data = (
        "institution_student_id,student_name,apaar_id,programme_id,academic_year,is_nri,seat_type\n"
        "APEX-NRI-001,NRI Candidate,987654321012,PROG-001-CSE,2026-2027,TRUE,REGULAR\n"
    )
    files = {"file": ("nri_mismatch.csv", csv_data, "text/csv")}
    import_res = client.post("/api/v1/imports", headers={"Authorization": f"Bearer {token}"}, files=files, data={"academic_year": "2026-2027"})
    batch_id = import_res.json()["batch_id"]

    val_res = client.post(f"/api/v1/batches/{batch_id}/validate", headers={"Authorization": f"Bearer {token}"})
    assert val_res.status_code == 200
    findings_res = client.get(f"/api/v1/batches/{batch_id}/findings", headers={"Authorization": f"Bearer {token}"})
    findings = findings_res.json()["items"]
    nri_findings = [f for f in findings if f["rule_code"] == "RULE-CAT-001"]
    assert len(nri_findings) == 1
    assert nri_findings[0]["severity"] == "WARNING"


# ==============================================================================
# 2. Intake-to-Enrolment Reconciliation Tests
# ==============================================================================
def test_intake_reconciliation_within_limits(client):
    """Batches within approved intake capacity report WITHIN_LIMIT status."""
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    # PROG-001-ECE has regular_intake: 60, supernumerary_intake: 6
    csv_data = (
        "institution_student_id,student_name,apaar_id,programme_id,academic_year,seat_type\n"
        "APEX-ECE-001,Student One,987654321012,PROG-001-ECE,2026-2027,REGULAR\n"
        "APEX-ECE-002,Student Two,111122223333,PROG-001-ECE,2026-2027,SUPERNUMERARY_EWS\n"
    )
    files = {"file": ("ece_valid.csv", csv_data, "text/csv")}
    import_res = client.post("/api/v1/imports", headers={"Authorization": f"Bearer {token}"}, files=files, data={"academic_year": "2026-2027"})
    batch_id = import_res.json()["batch_id"]

    val_res = client.post(f"/api/v1/batches/{batch_id}/validate", headers={"Authorization": f"Bearer {token}"})
    assert val_res.status_code == 200
    data = val_res.json()
    assert data["status"] == "VALIDATED"
    assert data["validation_summary"]["intake_exceeded_count"] == 0

    reconciliation = data["intake_reconciliation"]
    ece_rec = next(r for r in reconciliation if r["programme_id"] == "PROG-001-ECE")
    assert ece_rec["status"] == "WITHIN_LIMIT"
    assert ece_rec["regular_enrolled"] == 1
    assert ece_rec["supernumerary_enrolled"] == 1
    assert ece_rec["total_enrolled"] == 2
    assert ece_rec["total_exceeded"] == 0


def test_intake_reconciliation_exceeded_generates_blocking_finding(client):
    """Enrolment exceeding approved intake triggers RULE-INTAKE-001 (BLOCKING_ERROR)."""
    # Temporarily set approved intake for PROG-001-ME to 1 regular, 0 supernumerary
    db = SessionLocal()
    try:
        intake_me = db.query(ApprovedIntake).filter(
            ApprovedIntake.institution_id == "INST-001",
            ApprovedIntake.programme_id == "PROG-001-ME",
            ApprovedIntake.academic_year == "2026-2027"
        ).first()
        if intake_me:
            intake_me.regular_intake = 1
            intake_me.supernumerary_intake = 0
            db.commit()
    finally:
        db.close()

    token = get_auth_token(client, "apex_operator@apex.edu.in")
    # Enroll 2 regular students into PROG-001-ME (exceeds limit of 1)
    csv_data = (
        "institution_student_id,student_name,apaar_id,programme_id,academic_year,seat_type\n"
        "APEX-ME-001,Student One,987654321012,PROG-001-ME,2026-2027,REGULAR\n"
        "APEX-ME-002,Student Two,111122223333,PROG-001-ME,2026-2027,REGULAR\n"
    )
    files = {"file": ("me_overflow.csv", csv_data, "text/csv")}
    import_res = client.post("/api/v1/imports", headers={"Authorization": f"Bearer {token}"}, files=files, data={"academic_year": "2026-2027"})
    batch_id = import_res.json()["batch_id"]

    val_res = client.post(f"/api/v1/batches/{batch_id}/validate", headers={"Authorization": f"Bearer {token}"})
    assert val_res.status_code == 200
    data = val_res.json()
    assert data["status"] == "NEEDS_CORRECTION"
    assert data["validation_summary"]["intake_exceeded_count"] == 1

    me_rec = next(r for r in data["intake_reconciliation"] if r["programme_id"] == "PROG-001-ME")
    assert me_rec["status"] == "EXCEEDED"
    assert me_rec["total_enrolled"] == 2
    assert me_rec["total_approved"] == 1
    assert me_rec["total_exceeded"] == 1

    findings_res = client.get(f"/api/v1/batches/{batch_id}/findings", headers={"Authorization": f"Bearer {token}"})
    intake_findings = [f for f in findings_res.json()["items"] if f["rule_code"] == "RULE-INTAKE-001"]
    assert len(intake_findings) == 1
    assert intake_findings[0]["severity"] == "BLOCKING_ERROR"
    assert "exceeds approved AICTE intake" in intake_findings[0]["message"]


# ==============================================================================
# 3. Duplicate Detection & Cross-Institution Candidates
# ==============================================================================
def test_cross_institution_duplicate_apaar_creates_match_candidate(client):
    """Enrolling a student with the same APAAR ID across two different institutions flags a MatchCandidate."""
    # 1. Ingest into INST-001 (Apex)
    token_apex = get_auth_token(client, "apex_operator@apex.edu.in")
    csv_apex = (
        "institution_student_id,student_name,apaar_id,programme_id,academic_year\n"
        "APEX-CROSS-01,Shared Student,987654321012,PROG-001-CSE,2026-2027\n"
    )
    f1 = {"file": ("apex_cross.csv", csv_apex, "text/csv")}
    res1 = client.post("/api/v1/imports", headers={"Authorization": f"Bearer {token_apex}"}, files=f1, data={"academic_year": "2026-2027"})
    batch1_id = res1.json()["batch_id"]

    # 2. Ingest same APAAR ID into INST-002 (Bharat)
    token_bharat = get_auth_token(client, "bharat_admin@bharat.edu.in")
    csv_bharat = (
        "institution_student_id,student_name,apaar_id,programme_id,academic_year\n"
        "BHARAT-CROSS-01,Shared Student,987654321012,PROG-002-CSE,2026-2027\n"
    )
    f2 = {"file": ("bharat_cross.csv", csv_bharat, "text/csv")}
    res2 = client.post("/api/v1/imports", headers={"Authorization": f"Bearer {token_bharat}"}, files=f2, data={"academic_year": "2026-2027"})
    batch2_id = res2.json()["batch_id"]

    # Validate Batch 2
    val2 = client.post(f"/api/v1/batches/{batch2_id}/validate", headers={"Authorization": f"Bearer {token_bharat}"})
    assert val2.status_code == 200

    # Verify cross-institution duplicate finding
    findings_res = client.get(f"/api/v1/batches/{batch2_id}/findings", headers={"Authorization": f"Bearer {token_bharat}"})
    cross_finds = [f for f in findings_res.json()["items"] if f["rule_code"] == "RULE-DUP-005"]
    assert len(cross_finds) == 1
    assert cross_finds[0]["severity"] == "WARNING"
    assert "dual enrolment alert" in cross_finds[0]["message"].lower()

    # Verify MatchCandidate query endpoint
    matches_res = client.get(f"/api/v1/batches/{batch2_id}/matches", headers={"Authorization": f"Bearer {token_bharat}"})
    assert matches_res.status_code == 200
    matches = matches_res.json()["items"]
    assert len(matches) == 1
    assert matches[0]["matching_signal"] == "EXACT_APAAR_CROSS_INSTITUTION"
    assert matches[0]["status"] == "CANDIDATE"


# ==============================================================================
# 4. Security, Isolation & Audit Logging
# ==============================================================================
def test_cross_institution_validate_endpoint_strictly_forbidden(client):
    """An operator from INST-001 cannot trigger validation on an INST-002 batch."""
    token_bharat = get_auth_token(client, "bharat_admin@bharat.edu.in")
    csv_bharat = "institution_student_id,student_name,programme_id,academic_year\nB-01,Bharat Stu,PROG-002-CSE,2026-2027\n"
    files = {"file": ("b.csv", csv_bharat, "text/csv")}
    import_res = client.post("/api/v1/imports", headers={"Authorization": f"Bearer {token_bharat}"}, files=files, data={"academic_year": "2026-2027"})
    batch_id = import_res.json()["batch_id"]

    # Now attempt validation with apex_operator
    token_apex = get_auth_token(client, "apex_operator@apex.edu.in")
    denied = client.post(f"/api/v1/batches/{batch_id}/validate", headers={"Authorization": f"Bearer {token_apex}"})
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "INSTITUTION_SCOPE_VIOLATION"


def test_validation_creates_tamper_evident_audit_log(client):
    """Batch validation records an AuditEvent with action BATCH_VALIDATE."""
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    csv_data = "institution_student_id,student_name,programme_id,academic_year\nAPEX-AUD-001,Audit Student,PROG-001-CSE,2026-2027\n"
    files = {"file": ("aud.csv", csv_data, "text/csv")}
    import_res = client.post("/api/v1/imports", headers={"Authorization": f"Bearer {token}"}, files=files, data={"academic_year": "2026-2027"})
    batch_id = import_res.json()["batch_id"]

    client.post(f"/api/v1/batches/{batch_id}/validate", headers={"Authorization": f"Bearer {token}"})

    db = SessionLocal()
    try:
        audit = db.query(AuditEvent).filter(
            AuditEvent.action == AuditAction.BATCH_VALIDATE,
            AuditEvent.object_id == batch_id
        ).first()
        assert audit is not None
        assert audit.actor_email == "apex_operator@apex.edu.in"
        assert audit.institution_id == "INST-001"
        assert "validated" in audit.details.lower()
    finally:
        db.close()


# ==============================================================================
# 5. Phase 3 Remediation Regression Tests (P1-01, P1-02, P2-01)
# ==============================================================================
def test_cumulative_intake_across_multiple_batches(client):
    """
    P1-01 Remediation: Intake must calculate cumulative enrolment across batches for the same
    institution, programme and academic year without double counting.
    """
    # Use PROG-001-ECE for cumulative intake testing: Set regular intake to 2, supernumerary to 0
    db = SessionLocal()
    try:
        # Clear any prior student records in PROG-001-ECE for INST-001 so test is isolated
        db.query(StudentRecord).filter(
            StudentRecord.institution_id == "INST-001",
            StudentRecord.programme_id == "PROG-001-ECE",
            StudentRecord.academic_year == "2026-2027"
        ).delete()
        intake_ece = db.query(ApprovedIntake).filter(
            ApprovedIntake.institution_id == "INST-001",
            ApprovedIntake.programme_id == "PROG-001-ECE",
            ApprovedIntake.academic_year == "2026-2027"
        ).first()
        if intake_ece:
            intake_ece.regular_intake = 2
            intake_ece.supernumerary_intake = 0
            db.commit()
    finally:
        db.close()

    token = get_auth_token(client, "apex_operator@apex.edu.in")

    # Batch 1: Ingest 1 regular student (within limit 1/2) with unique synthetic APAAR
    csv_b1 = (
        "institution_student_id,student_name,apaar_id,programme_id,academic_year,seat_type\n"
        "APEX-CUMUL-01,Student First,888877776666,PROG-001-ECE,2026-2027,REGULAR\n"
    )
    res_b1 = client.post("/api/v1/imports", headers={"Authorization": f"Bearer {token}"}, files={"file": ("b1.csv", csv_b1, "text/csv")}, data={"academic_year": "2026-2027"})
    batch1_id = res_b1.json()["batch_id"]

    val_b1 = client.post(f"/api/v1/batches/{batch1_id}/validate", headers={"Authorization": f"Bearer {token}"})
    assert val_b1.status_code == 200
    assert val_b1.json()["status"] == "VALIDATED"
    ece_rec_b1 = next(r for r in val_b1.json()["intake_reconciliation"] if r["programme_id"] == "PROG-001-ECE")
    assert ece_rec_b1["total_enrolled"] == 1
    assert ece_rec_b1["status"] == "WITHIN_LIMIT"

    # Batch 2: Ingest 2 more regular students. Cumulative total is 1 + 2 = 3 > 2 (EXCEEDED)
    csv_b2 = (
        "institution_student_id,student_name,apaar_id,programme_id,academic_year,seat_type\n"
        "APEX-CUMUL-02,Student Second,888877776667,PROG-001-ECE,2026-2027,REGULAR\n"
        "APEX-CUMUL-03,Student Third,888877776668,PROG-001-ECE,2026-2027,REGULAR\n"
    )
    res_b2 = client.post("/api/v1/imports", headers={"Authorization": f"Bearer {token}"}, files={"file": ("b2.csv", csv_b2, "text/csv")}, data={"academic_year": "2026-2027"})
    batch2_id = res_b2.json()["batch_id"]

    val_b2 = client.post(f"/api/v1/batches/{batch2_id}/validate", headers={"Authorization": f"Bearer {token}"})
    assert val_b2.status_code == 200
    assert val_b2.json()["status"] == "NEEDS_CORRECTION"
    ece_rec_b2 = next(r for r in val_b2.json()["intake_reconciliation"] if r["programme_id"] == "PROG-001-ECE")
    assert ece_rec_b2["regular_enrolled"] == 3
    assert ece_rec_b2["regular_approved"] == 2
    assert ece_rec_b2["total_exceeded"] == 1
    assert ece_rec_b2["status"] == "EXCEEDED"


def test_accurate_source_row_numbers_when_prior_rows_rejected(client):
    """
    P1-02 Remediation: Phase 3 validation findings must reference the exact 1-based source spreadsheet
    row index even when earlier rows were malformed or rejected.
    """
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    # Row 1: Header
    # Row 2: Rejected row (Missing institution_student_id)
    # Row 3: Persisted row with short name (Triggers RULE-REQ-001 in validation)
    # Row 4: Persisted row with invalid APAAR checksum (Triggers RULE-APAAR-002 in validation)
    csv_data = (
        "institution_student_id,student_name,apaar_id,programme_id,academic_year\n"
        ",Student NoRoll,888899990001,PROG-001-CSE,2026-2027\n"
        "APEX-ROW-03,A,987654321012,PROG-001-CSE,2026-2027\n"
        "APEX-ROW-04,Valid Name,987654321019,PROG-001-CSE,2026-2027\n"
    )
    res = client.post("/api/v1/imports", headers={"Authorization": f"Bearer {token}"}, files={"file": ("rows.csv", csv_data, "text/csv")}, data={"academic_year": "2026-2027"})
    batch_id = res.json()["batch_id"]

    # Validate
    val = client.post(f"/api/v1/batches/{batch_id}/validate", headers={"Authorization": f"Bearer {token}"})
    assert val.status_code == 200

    findings_res = client.get(f"/api/v1/batches/{batch_id}/findings", headers={"Authorization": f"Bearer {token}"})
    findings = findings_res.json()["items"]

    # Ingestion rejected row 2 for missing student id
    f_row2 = [f for f in findings if f["rule_code"] == "RULE-REQ-002"]
    assert len(f_row2) == 1
    assert f_row2[0]["row_number"] == 2

    # Validation must report row 3 for short student name (NOT row 1!)
    f_row3 = [f for f in findings if f["rule_code"] == "RULE-REQ-001"]
    assert len(f_row3) == 1
    assert f_row3[0]["row_number"] == 3

    # Validation must report row 4 for bad checksum (NOT row 2!)
    f_row4 = [f for f in findings if f["rule_code"] == "RULE-APAAR-002"]
    assert len(f_row4) == 1
    assert f_row4[0]["row_number"] == 4


def test_match_candidate_symmetric_deduplication_and_repeated_validation(client):
    """
    P2-01 Remediation: MatchCandidate pairs must be checked symmetrically regardless of which institution
    validates first or if validation is run repeatedly, preserving resolved decisions.
    """
    token_apex = get_auth_token(client, "apex_operator@apex.edu.in")
    token_bharat = get_auth_token(client, "bharat_admin@bharat.edu.in")

    csv_apex = (
        "institution_student_id,student_name,apaar_id,programme_id,academic_year\n"
        "APEX-SYM-01,Shared Sym,987654321012,PROG-001-CSE,2026-2027\n"
    )
    res_a = client.post("/api/v1/imports", headers={"Authorization": f"Bearer {token_apex}"}, files={"file": ("sym_a.csv", csv_apex, "text/csv")}, data={"academic_year": "2026-2027"})
    batch_a_id = res_a.json()["batch_id"]

    csv_bharat = (
        "institution_student_id,student_name,apaar_id,programme_id,academic_year\n"
        "BHARAT-SYM-01,Shared Sym,987654321012,PROG-002-CSE,2026-2027\n"
    )
    res_b = client.post("/api/v1/imports", headers={"Authorization": f"Bearer {token_bharat}"}, files={"file": ("sym_b.csv", csv_bharat, "text/csv")}, data={"academic_year": "2026-2027"})
    batch_b_id = res_b.json()["batch_id"]

    # 1. Validate Batch B first
    val_b1 = client.post(f"/api/v1/batches/{batch_b_id}/validate", headers={"Authorization": f"Bearer {token_bharat}"})
    assert val_b1.status_code == 200

    matches_b1 = client.get(f"/api/v1/batches/{batch_b_id}/matches", headers={"Authorization": f"Bearer {token_bharat}"}).json()["items"]
    assert len(matches_b1) == 1
    match_id = matches_b1[0]["id"]

    # Mark the match as confirmed duplicate by a reviewer
    db = SessionLocal()
    try:
        cand = db.query(MatchCandidate).filter(MatchCandidate.id == match_id).first()
        cand.status = MatchStatus.CONFIRMED_DUPLICATE
        cand.resolution_reason = "Verified dual enrolment with Bharat Institute"
        db.commit()
    finally:
        db.close()

    # 2. Re-validate Batch B repeatedly: must NOT create another candidate or reset the reviewed status
    val_b2 = client.post(f"/api/v1/batches/{batch_b_id}/validate", headers={"Authorization": f"Bearer {token_bharat}"})
    assert val_b2.status_code == 200

    matches_b2 = client.get(f"/api/v1/batches/{batch_b_id}/matches", headers={"Authorization": f"Bearer {token_bharat}"}).json()["items"]
    assert len(matches_b2) == 1
    assert matches_b2[0]["id"] == match_id
    assert matches_b2[0]["status"] == "CONFIRMED_DUPLICATE"

    # 3. Validate Batch A (reverse order): must detect existing symmetric candidate and NOT insert a duplicate
    val_a = client.post(f"/api/v1/batches/{batch_a_id}/validate", headers={"Authorization": f"Bearer {token_apex}"})
    assert val_a.status_code == 200

    matches_a = client.get(f"/api/v1/batches/{batch_a_id}/matches", headers={"Authorization": f"Bearer {token_apex}"}).json()["items"]
    assert len(matches_a) == 1
    assert matches_a[0]["id"] == match_id


def test_multiple_blocking_findings_on_single_record_count_semantics(client):
    """
    Verify that a single record with multiple blocking findings (e.g. short name + malformed APAAR)
    only counts as 1 error row and does NOT double-subtract from valid_records count.
    Total: 2 records. Record 1: 2 blocking findings. Record 2: 0 findings (100% valid).
    Expected: valid_records == 1, error_rows == 1, total_records == 2.
    """
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    csv_data = (
        "institution_student_id,student_name,apaar_id,programme_id,academic_year\n"
        "APEX-MULTI-01,A,12345,PROG-001-CSE,2026-2027\n"  # 1 char name (< 2 chars) AND malformed APAAR (5 digits)
        "APEX-MULTI-02,Rajesh Kumar,987654321012,PROG-001-CSE,2026-2027\n"  # Valid record
    )
    files = {"file": ("multi_err_test.csv", csv_data, "text/csv")}
    import_res = client.post("/api/v1/imports", headers={"Authorization": f"Bearer {token}"}, files=files, data={"academic_year": "2026-2027"})
    assert import_res.status_code == 200
    batch_id = import_res.json()["batch_id"]

    val_res = client.post(f"/api/v1/batches/{batch_id}/validate", headers={"Authorization": f"Bearer {token}"})
    assert val_res.status_code == 200
    val_data = val_res.json()
    summary = val_data["validation_summary"]

    assert summary["total_records"] == 2
    # Distinct invalid records is 1, so valid_records must be exactly 1!
    assert summary["valid_records"] == 1
    # Error count represents total blocking findings (at least 2 findings on record 1)
    assert summary["error_count"] >= 2

    # Check batch model persistence
    db = SessionLocal()
    try:
        b = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
        assert b.total_rows == 2
        assert b.valid_rows == 1
        assert b.error_rows == 1
    finally:
        db.close()


def test_batch_validation_http_400_when_no_persisted_records(client):
    """
    Validate that triggering validation on a batch with 0 persisted student records
    (e.g. all rows rejected during import due to missing roll number / unapproved programme)
    returns HTTP 400 with the structured AppException envelope containing code 'EMPTY_BATCH'
    and a descriptive message.
    """
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    # All rows have missing student roll number -> 0 persisted student records
    csv_data = (
        "institution_student_id,student_name,programme_id,academic_year\n"
        ",Missing Roll Student 1,PROG-001-CSE,2026-2027\n"
        ",Missing Roll Student 2,PROG-001-CSE,2026-2027\n"
    )
    files = {"file": ("all_rejected.csv", csv_data, "text/csv")}
    import_res = client.post(
        "/api/v1/imports",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data={"academic_year": "2026-2027"}
    )
    assert import_res.status_code == 200
    batch_id = import_res.json()["batch_id"]
    assert import_res.json()["valid_rows"] == 0
    assert import_res.json()["error_rows"] == 2

    # Validation on this batch must return HTTP 400
    val_res = client.post(f"/api/v1/batches/{batch_id}/validate", headers={"Authorization": f"Bearer {token}"})
    assert val_res.status_code == 400
    val_err = val_res.json()
    assert "error" in val_err
    assert val_err["error"]["code"] == "EMPTY_BATCH"
    assert "no persisted student records" in val_err["error"]["message"]


def test_batch_validation_http_404_when_batch_not_found(client):
    """Validate that triggering validation on non-existent batch returns HTTP 404 with error envelope."""
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    val_res = client.post("/api/v1/batches/NON-EXISTENT-BATCH-999/validate", headers={"Authorization": f"Bearer {token}"})
    assert val_res.status_code == 404
    val_err = val_res.json()
    assert "error" in val_err
    assert val_err["error"]["code"] == "RESOURCE_NOT_FOUND"

