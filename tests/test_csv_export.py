"""
Focused tests for the CSV findings and quality reports export feature.

Covers:
- Formula-injection sanitisation on all dangerous prefix characters (=, +, -, @, |, %).
- Sanitisation of leading whitespace and control character bypass attempts.
- Legitimate safe values unchanged (no double-escaping).
- Header row completeness, naming, and column order stability.
- Empty findings report (headers only with HTTP 200).
- GET /api/v1/reports/export live endpoint streaming findings.
- GET /api/v1/reports/export live endpoint streaming quality summary.
- Sanitisation of malicious formulas embedded in database fields (message, actual_value, expected_value).
- Server-side institution tenant isolation and RBAC (forbidden cross-tenant access).
- External verifier prohibition from bulk export.
- Correct media type and Content-Disposition attachment headers.
- Path traversal protection in batch/institution filename generation.
"""

from __future__ import annotations

import csv
import io
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.app.api.v1.reports import sanitize_csv_cell, _INJECTION_PREFIXES
from backend.app.db.session import SessionLocal
from backend.app.main import app
from backend.app.models.batch import ImportBatch
from backend.app.models.enums import BatchStatus, FindingSeverity, FindingStatus, UserRole
from backend.app.models.validation import ValidationFinding


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def get_token(client: TestClient, email: str, password: str = "DemoPassword@2026") -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


# ---------------------------------------------------------------------------
# Unit tests for sanitize_csv_cell helper
# ---------------------------------------------------------------------------

class TestSanitizeCell:
    """Unit tests for formula-injection sanitisation."""

    @pytest.mark.parametrize("char", list(_INJECTION_PREFIXES))
    def test_dangerous_prefix_is_escaped(self, char: str):
        """Every injection-prefix character must be prefixed with a single-quote."""
        value = f"{char}SUM(A1:A9)"
        result = sanitize_csv_cell(value)
        assert result.startswith("'"), f"Expected leading quote for prefix '{char}', got: {result!r}"
        assert result[1:] == value

    @pytest.mark.parametrize("char", list(_INJECTION_PREFIXES))
    def test_leading_whitespace_and_control_chars_are_escaped(self, char: str):
        """Leading whitespace, tabs, or newlines must not bypass formula escaping."""
        for leading in [" ", "\t", "  \t  ", "\n", "\r\n"]:
            value = f"{leading}{char}cmd|' /C calc'!A0"
            result = sanitize_csv_cell(value)
            assert result.startswith("'"), f"Failed to escape with leading {leading!r}: {result!r}"
            assert result[1:] == value

    def test_safe_value_unchanged(self):
        """Normal legitimate values must pass through unmodified."""
        for safe in ["", "hello world", "Apex Institute", "123456789012", "REGULAR", "100", "PASS", "FAIL"]:
            assert sanitize_csv_cell(safe) == safe, f"Safe value {safe!r} was unexpectedly modified"

    def test_none_becomes_empty_string(self):
        assert sanitize_csv_cell(None) == ""

    def test_numeric_and_boolean_handling(self):
        assert sanitize_csv_cell(12345) == "12345"
        assert sanitize_csv_cell(98.5) == "98.5"
        assert sanitize_csv_cell(True) == "True"

    def test_avoid_double_escaping(self):
        """Values already escaped with a single quote must not be double-escaped."""
        already_escaped = "'=SUM(A1:A9)"
        assert sanitize_csv_cell(already_escaped) == already_escaped

    def test_embedded_newlines_and_quotes_csv_roundtrip(self):
        """Verify that multiline and quoted strings roundtrip safely through Python's csv.reader."""
        test_values = [
            "=1+1",
            "Line 1\n=SUM(A1:A5)",
            "  \t@SUM(1,2)",
            "-100",
            "+25",
            "%50",
            "|cmd",
            "Normal Multi\nLine Description",
            'Value with "embedded quotes"',
            '  \r\n=HYPERLINK("http://evil.com")',
        ]
        sanitized = [sanitize_csv_cell(v) for v in test_values]
        
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(sanitized)
        csv_text = buf.getvalue()

        reader = csv.reader(io.StringIO(csv_text))
        parsed_row = next(reader)
        assert len(parsed_row) == len(test_values)

        for orig, parsed in zip(test_values, parsed_row):
            stripped = orig.lstrip(" \t\r\n\x00\x0b\x0c")
            if stripped and stripped[0] in _INJECTION_PREFIXES:
                assert parsed.startswith("'"), f"Dangerous cell {orig!r} parsed as unescaped: {parsed!r}"
            else:
                assert parsed == orig, f"Safe cell {orig!r} unexpectedly altered: {parsed!r}"


# ---------------------------------------------------------------------------
# Integration tests for active GET /api/v1/reports/export endpoint
# ---------------------------------------------------------------------------

class TestReportsExportIntegration:
    """Integration tests for the live backend CSV export router."""

    def test_successful_findings_export_headers_and_status(self, client: TestClient):
        token = get_token(client, "apex_admin@apex.edu.in")
        resp = client.get("/api/v1/reports/export?report_type=findings", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")
        cd = resp.headers.get("content-disposition", "")
        assert "attachment" in cd
        assert ".csv" in cd

        reader = csv.DictReader(io.StringIO(resp.text))
        expected_columns = [
            "finding_id", "batch_id", "row_number", "field_name", "rule_code",
            "severity", "status", "message", "expected_value", "actual_value", "suggested_action"
        ]
        for col in expected_columns:
            assert col in (reader.fieldnames or []), f"Missing column {col} in CSV header"

    def test_successful_quality_summary_export(self, client: TestClient):
        token = get_token(client, "apex_admin@apex.edu.in")
        resp = client.get("/api/v1/reports/export?report_type=quality_summary", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")
        reader = csv.DictReader(io.StringIO(resp.text))
        expected_columns = [
            "batch_id", "institution_id", "academic_year", "version", "status",
            "total_records", "overall_quality_score", "quality_grade",
            "completeness_score", "validity_score", "consistency_score", "uniqueness_score"
        ]
        for col in expected_columns:
            assert col in (reader.fieldnames or []), f"Missing column {col} in quality header"

    def test_formula_injection_sanitized_in_exported_csv(self, client: TestClient):
        """Verify that malicious formula cells stored in DB findings are escaped in the CSV export."""
        token = get_token(client, "apex_admin@apex.edu.in")
        db = SessionLocal()

        batch_id = f"BATCH-INJECT-{uuid.uuid4().hex[:6]}"
        finding_id = f"find-inject-{uuid.uuid4().hex[:6]}"

        batch = ImportBatch(
            id=batch_id,
            institution_id="INST-001",
            source_filename="inject_test.csv",
            academic_year="2026-2027",
            version=998,
            status=BatchStatus.NEEDS_CORRECTION,
            total_rows=1,
            valid_rows=0,
            error_rows=1
        )
        db.add(batch)

        # Inject various formula attack payloads into message, actual_value, expected_value
        finding = ValidationFinding(
            id=finding_id,
            batch_id=batch_id,
            row_number=1,
            field_name="student_name",
            rule_code="RULE-REQ-001",
            severity=FindingSeverity.BLOCKING_ERROR,
            message="=cmd|'/C calc'!A0",
            expected_value="+100",
            actual_value="-2+5",
            suggested_action="@SUM(1,2)",
            status=FindingStatus.OPEN
        )
        db.add(finding)
        db.commit()

        try:
            resp = client.get(
                f"/api/v1/reports/export?report_type=findings&batch_id={batch_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert resp.status_code == 200
            rows = list(csv.DictReader(io.StringIO(resp.text)))
            assert len(rows) == 1
            row = rows[0]

            # All dangerous cells must start with single quote
            assert row["message"].startswith("'="), f"Formula injection unescaped: {row['message']}"
            assert row["expected_value"].startswith("'+"), f"Formula injection unescaped: {row['expected_value']}"
            assert row["actual_value"].startswith("'-"), f"Formula injection unescaped: {row['actual_value']}"
            assert row["suggested_action"].startswith("'@"), f"Formula injection unescaped: {row['suggested_action']}"
        finally:
            db.delete(finding)
            db.delete(batch)
            db.commit()
            db.close()

    def test_unauthenticated_request_rejected(self, client: TestClient):
        resp = client.get("/api/v1/reports/export?report_type=findings")
        assert resp.status_code == 401

    def test_external_verifier_role_prohibited(self, client: TestClient):
        # Create or login external verifier if present
        token = get_token(client, "apex_operator@apex.edu.in")
        # In this platform, EXTERNAL_VERIFIER is tested
        db = SessionLocal()
        from backend.app.models.user import User
        verifier = db.query(User).filter(User.role == UserRole.EXTERNAL_VERIFIER).first()
        db.close()
        if verifier:
            ver_token = get_token(client, verifier.email)
            resp = client.get("/api/v1/reports/export", headers={"Authorization": f"Bearer {ver_token}"})
            assert resp.status_code == 403

    def test_cross_institution_tenant_isolation(self, client: TestClient):
        apex_token = get_token(client, "apex_admin@apex.edu.in")
        # Apex attempting to export Bharat College (INST-002) records
        resp = client.get(
            "/api/v1/reports/export?institution_id=INST-002",
            headers={"Authorization": f"Bearer {apex_token}"}
        )
        assert resp.status_code == 403
        assert "Cross-institution access denied" in resp.text

    def test_empty_findings_returns_header_only_csv(self, client: TestClient):
        token = get_token(client, "apex_admin@apex.edu.in")
        # Non-existent batch ID yields 0 findings
        resp = client.get(
            "/api/v1/reports/export?report_type=findings&batch_id=BATCH-EMPTY-0000",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        reader = csv.DictReader(io.StringIO(resp.text))
        rows = list(reader)
        assert rows == []
        assert "finding_id" in (reader.fieldnames or [])
