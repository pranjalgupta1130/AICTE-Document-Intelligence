import io
import json
import zipfile
import xml.etree.ElementTree as ET
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.seed.seed_data import seed_database
from backend.app.db.session import SessionLocal
from backend.app.models.audit import AuditEvent
from backend.app.models.enums import AuditAction, BatchStatus, EnrolmentStatus, FindingSeverity, SeatType, UserRole
from backend.app.models.batch import ImportBatch
from backend.app.models.student import StudentRecord
from backend.app.models.validation import ValidationFinding
from backend.app.models.user import User
from backend.app.core.security import hash_password


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


def create_mock_xlsx(rows: list[list[str]]) -> bytes:
    """Helper to generate an in-memory .xlsx file without external dependencies."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        # [Content_Types].xml
        z.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
            '</Types>'
        )

        # _rels/.rels
        z.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'
        )

        # xl/_rels/workbook.xml.rels
        z.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
            '</Relationships>'
        )

        # xl/workbook.xml
        z.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/></sheets>'
            '</workbook>'
        )

        # Build sharedStrings and sheet1
        string_map = {}
        unique_strings = []

        sheet_xml = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>']
        for row_idx, row in enumerate(rows, start=1):
            sheet_xml.append(f'<row r="{row_idx}">')
            for col_idx, val in enumerate(row):
                if val not in string_map:
                    string_map[val] = len(unique_strings)
                    unique_strings.append(val)
                s_id = string_map[val]
                sheet_xml.append(f'<c t="s"><v>{s_id}</v></c>')
            sheet_xml.append('</row>')
        sheet_xml.append('</sheetData></worksheet>')

        sst_xml = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="{}">'.format(len(unique_strings))]
        for s in unique_strings:
            sst_xml.append(f'<si><t>{s}</t></si>')
        sst_xml.append('</sst>')

        z.writestr("xl/sharedStrings.xml", "".join(sst_xml))
        z.writestr("xl/worksheets/sheet1.xml", "".join(sheet_xml))

    return buf.getvalue()


# ==============================================================================
# 1. Template Download Tests
# ==============================================================================
def test_download_csv_template(client):
    """Verify CSV template download includes required AICTE fields."""
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    response = client.get("/api/v1/imports/template", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    content = response.text
    assert "apaar_id" in content
    assert "student_name" in content
    assert "institution_student_id" in content
    assert "programme_id" in content
    assert "academic_year" in content


def test_download_template_unauthorized(client):
    """Unauthenticated users cannot download import template."""
    response = client.get("/api/v1/imports/template")
    assert response.status_code == 401


# ==============================================================================
# 2. Preview Ingestion Tests
# ==============================================================================
def test_preview_valid_csv(client):
    """Verify preview parses valid CSV with suggested column mappings."""
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    csv_data = (
        "APAAR ID,Student Name,Roll No,Programme ID,Academic Year,Gender,Category,Email\n"
        "987654321012,John Doe,APEX-CS-2024-001,PROG-001-CSE,2026-2027,M,General,john@apex.edu.in\n"
        "987654321013,Jane Doe,APEX-CS-2024-002,PROG-001-CSE,2026-2027,F,OBC,jane@apex.edu.in\n"
    )
    files = {"file": ("students.csv", csv_data, "text/csv")}
    response = client.post("/api/v1/imports/preview", headers={"Authorization": f"Bearer {token}"}, files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "students.csv"
    assert data["total_preview_rows"] == 2
    assert len(data["sample_rows"]) == 2
    assert "apaar_id" in data["suggested_mapping"]
    assert data["suggested_mapping"]["apaar_id"] == "APAAR ID"
    assert data["suggested_mapping"]["institution_student_id"] == "Roll No"


def test_preview_valid_xlsx(client):
    """Verify preview parses valid XLSX file correctly."""
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    rows = [
        ["apaar_id", "student_name", "institution_student_id", "programme_id", "academic_year"],
        ["987654321014", "Xlsx User 1", "APEX-EC-001", "PROG-001-ECE", "2026-2027"],
    ]
    xlsx_bytes = create_mock_xlsx(rows)
    files = {"file": ("students.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    response = client.post("/api/v1/imports/preview", headers={"Authorization": f"Bearer {token}"}, files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "students.xlsx"
    assert data["total_preview_rows"] == 1
    assert data["sample_rows"][0]["apaar_id"] == "987654321014"


def test_preview_empty_file_rejected(client):
    """Verify empty file is rejected with 400 Bad Request."""
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    files = {"file": ("empty.csv", b"", "text/csv")}
    response = client.post("/api/v1/imports/preview", headers={"Authorization": f"Bearer {token}"}, files=files)
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "EMPTY_FILE"
    assert "empty" in data["error"]["message"].lower()


def test_preview_unsupported_file_type(client):
    """Verify non-CSV/XLSX files are rejected with 415."""
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    files = {"file": ("document.pdf", b"%PDF-1.4...", "application/pdf")}
    response = client.post("/api/v1/imports/preview", headers={"Authorization": f"Bearer {token}"}, files=files)
    assert response.status_code == 415
    data = response.json()
    assert data["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_preview_duplicate_headers(client):
    """Verify CSV with duplicate header names reports a structural error."""
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    csv_data = "student_name,student_name,roll_no\nAlice,Bob,101\n"
    files = {"file": ("duplicate.csv", csv_data, "text/csv")}
    response = client.post("/api/v1/imports/preview", headers={"Authorization": f"Bearer {token}"}, files=files)
    assert response.status_code == 200
    data = response.json()
    assert len(data["structural_errors"]) > 0
    assert "duplicate" in data["structural_errors"][0].lower()


# ==============================================================================
# 3. Commit Import Tests & Row Persistence
# ==============================================================================
def test_commit_valid_csv_import(client):
    """Test full import commit with valid records and verify DB persistence."""
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    csv_data = (
        "institution_student_id,student_name,apaar_id,programme_id,academic_year,gender,seat_type,enrolment_status\n"
        "APEX-TEST-001,Student One,111122223333,PROG-001-CSE,2026-2027,Male,Convener Quota,Admitted\n"
        "APEX-TEST-002,Student Two,111122223334,PROG-001-CSE,2026-2027,Female,Management Quota,Admitted\n"
        "APEX-TEST-003,Student Three,,PROG-001-CSE,2026-2027,Other,Supernumerary (TFW),Admitted\n"
    )
    files = {"file": ("test_students.csv", csv_data, "text/csv")}
    response = client.post(
        "/api/v1/imports",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data={"academic_year": "2026-2027"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["batch_id"] is not None
    assert data["version"] >= 1
    assert data["status"] == "DRAFT"
    assert data["total_rows"] == 3
    assert data["valid_rows"] == 3
    assert data["error_rows"] == 0
    assert len(data["row_errors"]) == 0

    # Verify records in database
    db = SessionLocal()
    try:
        records = db.query(StudentRecord).filter(
            StudentRecord.institution_student_id.in_(["APEX-TEST-001", "APEX-TEST-002", "APEX-TEST-003"])
        ).all()
        assert len(records) == 3
        s1 = next(r for r in records if r.institution_student_id == "APEX-TEST-001")
        assert s1.apaar_id == "111122223333"
        assert s1.student_name == "Student One"
        assert s1.programme_id == "PROG-001-CSE"
        assert s1.institution_id == "INST-001"
        assert s1.seat_type == SeatType.REGULAR
        assert s1.enrolment_status == EnrolmentStatus.ADMITTED

        # Verify audit event was logged
        audit = db.query(AuditEvent).filter(
            AuditEvent.action == AuditAction.IMPORT_UPLOAD,
            AuditEvent.object_id == data["batch_id"]
        ).first()
        assert audit is not None
        assert audit.institution_id == "INST-001"
    finally:
        db.close()


def test_commit_version_increment(client):
    """Test that importing for the same institution and academic year increments version."""
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    csv_data = (
        "institution_student_id,student_name,programme_id,academic_year\n"
        "APEX-V2-001,Version Two Student,PROG-001-CSE,2026-2027\n"
    )
    files = {"file": ("version2.csv", csv_data, "text/csv")}
    response = client.post(
        "/api/v1/imports",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data={"academic_year": "2026-2027"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["version"] >= 2


def test_commit_mixed_valid_and_invalid_rows(client):
    """Test importing mixed data: valid rows persist, invalid rows create row-level findings."""
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    csv_data = (
        "institution_student_id,student_name,programme_id,academic_year\n"
        "APEX-MIX-001,Valid Student,PROG-001-CSE,2026-2027\n"
        ",Missing Roll Student,PROG-001-CSE,2026-2027\n"
        "APEX-MIX-003,Bad Prog Student,PROG-INVALID-XYZ,2026-2027\n"
    )
    files = {"file": ("mixed.csv", csv_data, "text/csv")}
    response = client.post(
        "/api/v1/imports",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data={"academic_year": "2026-2027"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 3
    assert data["valid_rows"] == 1
    assert data["error_rows"] == 2
    assert len(data["row_errors"]) == 2

    row_numbers = [e["row_number"] for e in data["row_errors"]]
    assert 3 in row_numbers
    assert 4 in row_numbers

    # Verify findings persisted in database
    db = SessionLocal()
    try:
        findings = db.query(ValidationFinding).filter(ValidationFinding.batch_id == data["batch_id"]).all()
        assert len(findings) == 2
        messages = [f.message for f in findings]
        assert any("institution student" in m.lower() for m in messages)
        assert any("programme" in m.lower() for m in messages)
    finally:
        db.close()


def test_commit_with_custom_column_mapping(client):
    """Test import commit with custom column mapping parameter."""
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    csv_data = (
        "CustomRoll,CustomName,CustomProg,CustomYear\n"
        "APEX-CUST-001,Custom Mapped Student,PROG-001-CSE,2026-2027\n"
    )
    mapping = {
        "institution_student_id": "CustomRoll",
        "student_name": "CustomName",
        "programme_id": "CustomProg",
        "academic_year": "CustomYear"
    }
    files = {"file": ("custom.csv", csv_data, "text/csv")}
    response = client.post(
        "/api/v1/imports",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data={"mapping": json.dumps(mapping)}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid_rows"] == 1
    assert data["error_rows"] == 0


# ==============================================================================
# 4. Access Control & Cross-Institution Isolation Tests
# ==============================================================================
def test_cross_institution_import_tampering_blocked(client):
    """Test that an institution operator CANNOT import data into another institution."""
    token = get_auth_token(client, "apex_operator@apex.edu.in")  # INST-001
    csv_data = "institution_student_id,student_name,programme_id\nTEST-01,Test,PROG-002-CSE\n"
    files = {"file": ("spoof.csv", csv_data, "text/csv")}
    # Attempt to target INST-002 (Bharat Institute)
    response = client.post(
        "/api/v1/imports",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data={"institution_id": "INST-002", "academic_year": "2026-2027"}
    )
    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "INSTITUTION_SCOPE_VIOLATION"
    assert "cross-institution" in data["error"]["message"].lower()


def test_external_verifier_cannot_import(client):
    """External verifier role cannot initiate student data imports."""
    db = SessionLocal()
    verifier_email = "verifier_test_p2@external.gov.in"
    try:
        user = db.query(User).filter(User.email == verifier_email).first()
        if not user:
            user = User(
                id="usr-verifier-p2",
                email=verifier_email,
                hashed_password=hash_password("DemoPassword@2026"),
                full_name="External Auditor P2",
                role=UserRole.EXTERNAL_VERIFIER,
                institution_id=None,
                is_active=True
            )
            db.add(user)
            db.commit()

        token = get_auth_token(client, verifier_email)
        csv_data = "institution_student_id,student_name\nTEST-01,Test\n"
        files = {"file": ("verifier.csv", csv_data, "text/csv")}
        response = client.post("/api/v1/imports", headers={"Authorization": f"Bearer {token}"}, files=files)
        assert response.status_code == 403
        data = response.json()
        assert data["error"]["code"] == "PERMISSION_DENIED"
    finally:
        db.close()


def test_unauthenticated_import_rejected(client):
    """Unauthenticated request to import endpoint is rejected with 401."""
    csv_data = "institution_student_id,student_name\nTEST-01,Test\n"
    files = {"file": ("unauth.csv", csv_data, "text/csv")}
    response = client.post("/api/v1/imports", files=files)
    assert response.status_code == 401


# ==============================================================================
# 5. Batches & Findings Scoped Queries
# ==============================================================================
def test_batches_list_scoped_to_institution(client):
    """Verify GET /api/v1/batches returns only batches of the caller's institution."""
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    response = client.get("/api/v1/batches", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    res_data = response.json()
    assert "items" in res_data
    items = res_data["items"]
    assert len(items) > 0
    for b in items:
        assert b["institution_id"] == "INST-001"


def test_batch_detail_cross_institution_blocked(client):
    """Verify an operator from INST-002 cannot read a batch belonging to INST-001."""
    # First get an INST-001 batch id
    token_apex = get_auth_token(client, "apex_operator@apex.edu.in")
    resp_apex = client.get("/api/v1/batches", headers={"Authorization": f"Bearer {token_apex}"})
    batches = resp_apex.json()["items"]
    assert len(batches) > 0
    batch_id = batches[0]["id"]

    # Now attempt access using bharat_admin (INST-002)
    token_bharat = get_auth_token(client, "bharat_admin@bharat.edu.in")
    response = client.get(f"/api/v1/batches/{batch_id}", headers={"Authorization": f"Bearer {token_bharat}"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INSTITUTION_SCOPE_VIOLATION"


def test_batch_findings_endpoint_and_isolation(client):
    """Verify GET /api/v1/batches/{id}/findings returns findings and enforces isolation."""
    # Create an import with error to ensure findings exist
    token_apex = get_auth_token(client, "apex_operator@apex.edu.in")
    csv_data = "institution_student_id,student_name,programme_id\n,Missing Student,PROG-001-CSE\n"
    files = {"file": ("err.csv", csv_data, "text/csv")}
    commit_res = client.post(
        "/api/v1/imports",
        headers={"Authorization": f"Bearer {token_apex}"},
        files=files,
        data={"academic_year": "2026-2027"}
    )
    batch_id = commit_res.json()["batch_id"]

    # Fetch findings as APEX operator
    findings_res = client.get(f"/api/v1/batches/{batch_id}/findings", headers={"Authorization": f"Bearer {token_apex}"})
    assert findings_res.status_code == 200
    res_data = findings_res.json()
    assert "items" in res_data
    findings = res_data["items"]
    assert len(findings) >= 1
    assert findings[0]["batch_id"] == batch_id
    assert findings[0]["severity"] == "BLOCKING_ERROR"

    # Fetch findings as BHARAT admin -> should be forbidden
    token_bharat = get_auth_token(client, "bharat_admin@bharat.edu.in")
    denied_res = client.get(f"/api/v1/batches/{batch_id}/findings", headers={"Authorization": f"Bearer {token_bharat}"})
    assert denied_res.status_code == 403
    assert denied_res.json()["error"]["code"] == "INSTITUTION_SCOPE_VIOLATION"


def test_aicte_admin_can_access_any_batch_and_findings(client):
    """AICTE admin can view any batch across any institution."""
    token_admin = get_auth_token(client, "aicte_admin@aicte.gov.in")
    response = client.get("/api/v1/batches", headers={"Authorization": f"Bearer {token_admin}"})
    assert response.status_code == 200
    batches = response.json()["items"]
    assert len(batches) > 0
    batch_id = batches[0]["id"]

    detail_res = client.get(f"/api/v1/batches/{batch_id}", headers={"Authorization": f"Bearer {token_admin}"})
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == batch_id


# ==============================================================================
# 6. Remediation Regression Tests (P1 & P2 Fixes)
# ==============================================================================
def test_preview_does_not_mutate_database(client):
    """Prove that previewing a file does NOT create batches or student records."""
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    csv_data = "institution_student_id,student_name,programme_id\nPREV-001,Preview Candidate,PROG-001-CSE\n"
    files = {"file": ("preview_only.csv", csv_data, "text/csv")}

    db = SessionLocal()
    try:
        batches_before = db.query(ImportBatch).count()
        students_before = db.query(StudentRecord).count()

        resp = client.post("/api/v1/imports/preview", headers={"Authorization": f"Bearer {token}"}, files=files)
        assert resp.status_code == 200

        batches_after = db.query(ImportBatch).count()
        students_after = db.query(StudentRecord).count()

        assert batches_after == batches_before
        assert students_after == students_before
    finally:
        db.close()


def test_upload_streaming_size_limit_preview(client, monkeypatch):
    """Enforce upload size limit on preview route (HTTP 413)."""
    from backend.app.core.config import settings
    monkeypatch.setattr(settings, "MAX_CSV_UPLOAD_BYTES", 500)

    token = get_auth_token(client, "apex_operator@apex.edu.in")
    oversized_data = "a" * 600
    files = {"file": ("big.csv", oversized_data, "text/csv")}
    resp = client.post("/api/v1/imports/preview", headers={"Authorization": f"Bearer {token}"}, files=files)
    assert resp.status_code == 413
    assert resp.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_upload_streaming_size_limit_commit(client, monkeypatch):
    """Enforce upload size limit on commit route while reading data (HTTP 413)."""
    from backend.app.core.config import settings
    monkeypatch.setattr(settings, "MAX_CSV_UPLOAD_BYTES", 500)

    token = get_auth_token(client, "apex_operator@apex.edu.in")
    oversized_data = "institution_student_id,student_name,programme_id\n" + ("X" * 600)
    files = {"file": ("big_commit.csv", oversized_data, "text/csv")}
    resp = client.post("/api/v1/imports", headers={"Authorization": f"Bearer {token}"}, files=files)
    assert resp.status_code == 413
    assert resp.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_xlsx_sparse_cells_preserve_coordinates(client):
    """Verify XLSX parser respects explicit column coordinates when intervening cells are empty."""
    token = get_auth_token(client, "apex_operator@apex.edu.in")

    # Generate custom XLSX with sparse row: Col A=Roll, Col B=(empty), Col C=Programme
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
            '</Types>'
        )
        z.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'
        )
        z.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
            '</Relationships>'
        )
        z.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/></sheets>'
            '</workbook>'
        )
        sst = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="4">'
            '<si><t>institution_student_id</t></si>'
            '<si><t>student_name</t></si>'
            '<si><t>programme_id</t></si>'
            '<si><t>APEX-SPARSE-001</t></si>'
            '<si><t>PROG-001-CSE</t></si>'
            '</sst>'
        )
        z.writestr("xl/sharedStrings.xml", sst)

        # Row 1: A1=roll, B1=name, C1=programme
        # Row 2: A2=APEX-SPARSE-001, B2 is OMITTED, C2=PROG-001-CSE
        sheet_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheetData>'
            '<row r="1">'
            '<c r="A1" t="s"><v>0</v></c>'
            '<c r="B1" t="s"><v>1</v></c>'
            '<c r="C1" t="s"><v>2</v></c>'
            '</row>'
            '<row r="2">'
            '<c r="A2" t="s"><v>3</v></c>'
            '<c r="C2" t="s"><v>4</v></c>'
            '</row>'
            '</sheetData>'
            '</worksheet>'
        )
        z.writestr("xl/worksheets/sheet1.xml", sheet_xml)

    files = {"file": ("sparse.xlsx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    resp = client.post("/api/v1/imports/preview", headers={"Authorization": f"Bearer {token}"}, files=files)
    assert resp.status_code == 200
    data = resp.json()
    sample = data["sample_rows"][0]
    assert sample["institution_student_id"] == "APEX-SPARSE-001"
    assert sample["student_name"] == ""  # Empty because B2 was omitted
    assert sample["programme_id"] == "PROG-001-CSE"  # Preserved in col C


def test_intra_file_duplicate_roll_number_detection(client):
    """Duplicate roll numbers within single file produce BLOCKING_ERROR finding and are not persisted twice."""
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    csv_data = (
        "institution_student_id,student_name,programme_id,academic_year\n"
        "APEX-DUP-001,Alice,PROG-001-CSE,2026-2027\n"
        "APEX-DUP-001,Alice Duplicate,PROG-001-CSE,2026-2027\n"
    )
    files = {"file": ("dup_roll.csv", csv_data, "text/csv")}
    resp = client.post("/api/v1/imports", headers={"Authorization": f"Bearer {token}"}, files=files, data={"academic_year": "2026-2027"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_rows"] == 2
    assert data["valid_rows"] == 1
    assert data["error_rows"] == 1
    assert any("duplicate" in e["message"].lower() for e in data["row_errors"])


def test_intra_file_duplicate_apaar_id_detection(client):
    """Duplicate APAAR IDs within single file produce BLOCKING_ERROR finding."""
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    csv_data = (
        "institution_student_id,student_name,apaar_id,programme_id,academic_year\n"
        "APEX-APAAR-001,Bob One,999888777666,PROG-001-CSE,2026-2027\n"
        "APEX-APAAR-002,Bob Two,999888777666,PROG-001-CSE,2026-2027\n"
    )
    files = {"file": ("dup_apaar.csv", csv_data, "text/csv")}
    resp = client.post("/api/v1/imports", headers={"Authorization": f"Bearer {token}"}, files=files, data={"academic_year": "2026-2027"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_rows"] == 2
    assert data["valid_rows"] == 1
    assert data["error_rows"] == 1
    assert any("duplicate apaar" in e["message"].lower() for e in data["row_errors"])


def test_historical_duplicate_student_id_detection(client):
    """Uploading a roll number previously persisted in an earlier batch generates a duplicate finding."""
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    # First batch
    csv_b1 = "institution_student_id,student_name,programme_id,academic_year\nAPEX-HIST-001,Carol,PROG-001-CSE,2026-2027\n"
    f1 = {"file": ("b1.csv", csv_b1, "text/csv")}
    resp1 = client.post("/api/v1/imports", headers={"Authorization": f"Bearer {token}"}, files=f1, data={"academic_year": "2026-2027"})
    assert resp1.status_code == 200
    assert resp1.json()["valid_rows"] == 1

    # Second batch attempting same roll number
    csv_b2 = "institution_student_id,student_name,programme_id,academic_year\nAPEX-HIST-001,Carol Re-upload,PROG-001-CSE,2026-2027\n"
    f2 = {"file": ("b2.csv", csv_b2, "text/csv")}
    resp2 = client.post("/api/v1/imports", headers={"Authorization": f"Bearer {token}"}, files=f2, data={"academic_year": "2026-2027"})
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["valid_rows"] == 0
    assert data["error_rows"] == 1
    assert any("already exists" in e["message"].lower() for e in data["row_errors"])


def test_atomic_rollback_on_database_failure(client, monkeypatch):
    """Prove that an unhandled database failure triggers rollback leaving NO partial records."""
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    csv_data = "institution_student_id,student_name,programme_id,academic_year\nAPEX-FAIL-001,Dave,PROG-001-CSE,2026-2027\n"
    files = {"file": ("fail.csv", csv_data, "text/csv")}

    from sqlalchemy.orm import Session
    orig_commit = Session.commit

    def broken_commit(self):
        raise Exception("Simulated DB lock or disk I/O error during commit")

    monkeypatch.setattr(Session, "commit", broken_commit)

    db = SessionLocal()
    try:
        batches_before = db.query(ImportBatch).count()
        students_before = db.query(StudentRecord).count()

        resp = client.post("/api/v1/imports", headers={"Authorization": f"Bearer {token}"}, files=files, data={"academic_year": "2026-2027"})
        assert resp.status_code == 500
        assert "FAILED" in resp.json()["error"]["code"]

        batches_after = db.query(ImportBatch).count()
        students_after = db.query(StudentRecord).count()

        assert batches_after == batches_before
        assert students_after == students_before
    finally:
        db.close()


def test_csv_rfc4180_multiline_and_crlf(client):
    """Test CSV with CRLF line endings and quoted multi-line fields."""
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    csv_data = (
        'institution_student_id,student_name,programme_id,academic_year\r\n'
        'APEX-RFC-001,"Student With\r\nMultiline Name",PROG-001-CSE,2026-2027\r\n'
        'APEX-RFC-002,"Quoted, Comma Name",PROG-001-CSE,2026-2027\r\n'
    )
    files = {"file": ("rfc.csv", csv_data, "text/csv")}
    resp = client.post("/api/v1/imports", headers={"Authorization": f"Bearer {token}"}, files=files, data={"academic_year": "2026-2027"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_rows"] == 2
    assert data["valid_rows"] == 2


def test_import_with_quota_type_column_header(client):
    """
    P3-03 Verification Test:
    - Verifies that external spreadsheet files using 'quota_type' or 'quota' as the column
      header are successfully mapped to the canonical 'seat_type' database field.
    """
    token = get_auth_token(client, "apex_operator@apex.edu.in")
    csv_data = (
        "institution_student_id,student_name,programme_id,academic_year,quota_type\n"
        "APEX-QUOTA-01,Quota Student,PROG-001-CSE,2026-2027,MANAGEMENT\n"
    )
    files = {"file": ("quota_test.csv", csv_data, "text/csv")}
    resp = client.post("/api/v1/imports", headers={"Authorization": f"Bearer {token}"}, files=files, data={"academic_year": "2026-2027"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_rows"] == 1
    assert data["valid_rows"] == 1

    # Check imported record in database
    db = SessionLocal()
    try:
        rec = db.query(StudentRecord).filter(StudentRecord.institution_student_id == "APEX-QUOTA-01").first()
        assert rec is not None
        assert rec.seat_type == SeatType.MANAGEMENT
    finally:
        if rec:
            db.delete(rec)
            db.commit()
        db.close()
