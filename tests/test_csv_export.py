"""Focused tests for the CSV findings export feature.

Covers:
- Successful export of a full PipelineRunResult (headers + data rows).
- Column-header completeness and order.
- Empty-findings scenario (headers only, HTTP 200).
- Formula-injection sanitisation on all dangerous prefix characters.
- Authorization / institution isolation: the endpoint trusts the caller to
  apply RBAC; we document this by testing that arbitrary application_id
  values are accepted (isolation is the callers' responsibility) and that a
  malformed payload is rejected with HTTP 422.
- Invalid / missing required fields → HTTP 422.
- Content-Disposition header and media-type.
- All three finding sections: regulatory, consistency, and duplicate.

All test data is fully synthetic – no real student PII is used.
"""

from __future__ import annotations

import csv
import io
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from verireg.api import router
from verireg.csv_export import ALL_COLUMNS, _INJECTION_PREFIXES, _sanitize, build_findings_csv
from verireg.schemas import (
    CrossDocConsistencyResult,
    DocumentAnalysisResult,
    DocumentMetadata,
    DigitalSignatureInfo,
    DuplicateDetectionResult,
    PipelineRunResult,
    RegulatoryCheckResult,
    RiskTier,
    SeverityLevel,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def api_client() -> TestClient:
    """Returns a TestClient wired to the member-1 router."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/member1")
    return TestClient(app)


def _minimal_doc_analysis() -> DocumentAnalysisResult:
    """Minimal synthetic DocumentAnalysisResult with no real PII."""
    return DocumentAnalysisResult(
        metadata=DocumentMetadata(
            filename="synthetic_test.pdf",
            sha256_hash="a" * 64,
            total_pages=1,
            file_size_bytes=1024,
            is_pdf=True,
        ),
        pages=[],
        extracted_fields={},
        signatures=DigitalSignatureInfo(),
    )


def _minimal_pipeline_result(application_id: str = "TEST-APP-EXPORT-01") -> PipelineRunResult:
    """A minimal but schema-valid PipelineRunResult with at least one of each finding type."""
    reg_check = RegulatoryCheckResult(
        rule_id="RULE-LAND-001",
        rule_name="Minimum Contiguous Land Requirement",
        rule_category="Land",
        status="FAIL",
        severity=SeverityLevel.DEFICIENCY,
        statutory_standard=">= 2.5 acres (Configured default)",
        is_authoritatively_verified=False,
        observed_value="1.2 acres",
        difference="-1.30 acres",
        deficiency_reason="Land area 1.2 acres is below the 2.5 acres requirement.",
        evidence=[],
    )

    consistency_check = CrossDocConsistencyResult(
        check_name="Institution Name Match",
        field_compared="institution_name",
        is_consistent=False,
        discrepancy_details="'NIT Trichy' vs 'NITT'",
        severity=SeverityLevel.CRITICAL,
        documents_involved=["doc_a.pdf", "doc_b.pdf"],
        evidences=[],
    )

    dup_result = DuplicateDetectionResult(
        exact_duplicates=[
            {
                "documents": ["doc_a.pdf", "doc_a_copy.pdf"],
                "sha256_hash": "b" * 64,
            }
        ],
        perceptual_image_duplicates=[
            {
                "documents": ["doc_a.pdf", "doc_c.pdf"],
                "hamming_distance": 3,
            }
        ],
        has_duplicate_findings=True,
    )

    return PipelineRunResult(
        application_id=application_id,
        analyzed_documents=[_minimal_doc_analysis()],
        rule_evaluations=[reg_check],
        consistency_evaluations=[consistency_check],
        duplicate_evaluations=dup_result,
        risk_tier=RiskTier.ESCALATION,
        risk_score=85.0,
        findings_audit_trail=[{"finding": "RULE-LAND-001", "score_penalty": 85.0}],
        critical_deficiencies=["Fire NOC missing"],
        clarification_notes=[],
        recommendations=["Obtain Fire NOC before resubmission."],
    )


def _empty_pipeline_result(application_id: str = "TEST-APP-EMPTY") -> PipelineRunResult:
    """A PipelineRunResult with zero findings of any kind."""
    return PipelineRunResult(
        application_id=application_id,
        analyzed_documents=[],
        rule_evaluations=[],
        consistency_evaluations=[],
        duplicate_evaluations=DuplicateDetectionResult(
            exact_duplicates=[],
            perceptual_image_duplicates=[],
            has_duplicate_findings=False,
        ),
        risk_tier=RiskTier.ACCELERATED,
        risk_score=0.0,
        findings_audit_trail=[],
        critical_deficiencies=[],
        clarification_notes=[],
        recommendations=[],
    )


# ---------------------------------------------------------------------------
# Unit tests for csv_export helpers
# ---------------------------------------------------------------------------


class TestSanitize:
    """Unit tests for formula-injection sanitisation."""

    @pytest.mark.parametrize("char", list(_INJECTION_PREFIXES))
    def test_dangerous_prefix_is_escaped(self, char: str):
        """Every injection-prefix character must be prefixed with a single-quote."""
        value = f"{char}SUM(A1:A9)"
        result = _sanitize(value)
        assert result.startswith("'"), f"Expected leading quote for prefix '{char}', got: {result!r}"
        assert result[1:] == value

    def test_safe_value_unchanged(self):
        """Normal values must pass through unmodified."""
        for safe in ["", "hello world", "NIT Trichy", "1.5 acres", "100", "PASS", "FAIL"]:
            assert _sanitize(safe) == safe, f"Safe value {safe!r} was unexpectedly modified"

    def test_none_becomes_empty_string(self):
        assert _sanitize(None) == ""

    def test_numeric_becomes_string(self):
        assert _sanitize(42) == "42"
        assert _sanitize(3.14) == "3.14"

    def test_deeply_nested_formula_prefix(self):
        """Only the first character triggers the prefix – not internal ones."""
        value = "normal=still_safe"
        assert _sanitize(value) == "normal=still_safe"


class TestBuildFindingsCsv:
    """Unit tests for the build_findings_csv function."""

    def test_header_row_contains_all_columns(self):
        result = _empty_pipeline_result()
        csv_text = build_findings_csv(result)
        reader = csv.DictReader(io.StringIO(csv_text))
        assert reader.fieldnames is not None
        for col in ALL_COLUMNS:
            assert col in reader.fieldnames, f"Missing column: {col}"

    def test_empty_findings_returns_header_only(self):
        result = _empty_pipeline_result()
        csv_text = build_findings_csv(result)
        reader = csv.DictReader(io.StringIO(csv_text))
        rows = list(reader)
        assert rows == [], f"Expected no data rows, got: {rows}"

    def test_regulatory_finding_produces_row(self):
        result = _minimal_pipeline_result()
        csv_text = build_findings_csv(result)
        reader = csv.DictReader(io.StringIO(csv_text))
        rows = list(reader)
        reg_rows = [r for r in rows if r["finding_type"] == "REGULATORY_RULE"]
        assert len(reg_rows) == 1
        row = reg_rows[0]
        assert row["rule_id"] == "RULE-LAND-001"
        assert row["status"] == "FAIL"
        assert row["severity"] == "DEFICIENCY"
        assert row["application_id"] == "TEST-APP-EXPORT-01"
        assert row["is_authoritatively_verified"] == "False"

    def test_consistency_finding_produces_row(self):
        result = _minimal_pipeline_result()
        csv_text = build_findings_csv(result)
        reader = csv.DictReader(io.StringIO(csv_text))
        rows = [r for r in reader if r["finding_type"] == "CONSISTENCY_CHECK"]
        assert len(rows) == 1
        row = rows[0]
        assert row["field_compared"] == "institution_name"
        assert row["is_consistent"] == "False"
        assert "NIT Trichy" in row["discrepancy_details"]

    def test_duplicate_findings_produce_rows(self):
        result = _minimal_pipeline_result()
        csv_text = build_findings_csv(result)
        reader = csv.DictReader(io.StringIO(csv_text))
        dup_rows = [r for r in reader if r["finding_type"] == "DUPLICATE_DETECTION"]
        assert len(dup_rows) == 2  # 1 exact + 1 perceptual
        types = {r["duplicate_type"] for r in dup_rows}
        assert "EXACT_SHA256" in types
        assert "PERCEPTUAL_IMAGE" in types

    def test_total_row_count(self):
        """1 regulatory + 1 consistency + 2 duplicate = 4 data rows."""
        result = _minimal_pipeline_result()
        csv_text = build_findings_csv(result)
        reader = csv.DictReader(io.StringIO(csv_text))
        assert len(list(reader)) == 4

    def test_formula_injection_in_deficiency_reason(self):
        """A malicious deficiency_reason starting with '=' must be sanitised."""
        result = _minimal_pipeline_result()
        # Inject a formula into deficiency_reason of the first rule
        result.rule_evaluations[0].deficiency_reason = "=cmd|' /C calc'!A0"
        csv_text = build_findings_csv(result)
        reader = csv.DictReader(io.StringIO(csv_text))
        rows = [r for r in reader if r["finding_type"] == "REGULATORY_RULE"]
        assert len(rows) == 1
        # The value in deficiency_reason column must start with "'"
        assert rows[0]["deficiency_reason"].startswith("'"), (
            f"Formula not sanitised: {rows[0]['deficiency_reason']!r}"
        )

    def test_column_order_is_stable(self):
        """DictWriter must emit columns in the canonical ALL_COLUMNS order."""
        result = _minimal_pipeline_result()
        csv_text = build_findings_csv(result)
        first_line = csv_text.splitlines()[0]
        actual_cols = first_line.split(",")
        assert actual_cols == ALL_COLUMNS

    def test_application_id_in_every_row(self):
        result = _minimal_pipeline_result(application_id="INST-A-BATCH-99")
        csv_text = build_findings_csv(result)
        reader = csv.DictReader(io.StringIO(csv_text))
        for row in reader:
            assert row["application_id"] == "INST-A-BATCH-99"


# ---------------------------------------------------------------------------
# Integration tests via the FastAPI TestClient
# ---------------------------------------------------------------------------


class TestExportEndpointIntegration:
    """Integration tests hitting POST /api/v1/member1/export-findings-csv."""

    def test_successful_export_status_code(self, api_client: TestClient):
        payload = _minimal_pipeline_result().model_dump()
        resp = api_client.post("/api/v1/member1/export-findings-csv", json=payload)
        assert resp.status_code == 200, resp.text

    def test_content_type_is_csv(self, api_client: TestClient):
        payload = _minimal_pipeline_result().model_dump()
        resp = api_client.post("/api/v1/member1/export-findings-csv", json=payload)
        assert "text/csv" in resp.headers.get("content-type", "")

    def test_content_disposition_attachment(self, api_client: TestClient):
        payload = _minimal_pipeline_result(application_id="TEST-DISP-01").model_dump()
        resp = api_client.post("/api/v1/member1/export-findings-csv", json=payload)
        cd = resp.headers.get("content-disposition", "")
        assert "attachment" in cd
        assert "findings_TEST-DISP-01.csv" in cd

    def test_response_body_is_valid_csv(self, api_client: TestClient):
        payload = _minimal_pipeline_result().model_dump()
        resp = api_client.post("/api/v1/member1/export-findings-csv", json=payload)
        text = resp.text
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        assert len(rows) == 4  # 1 regulatory + 1 consistency + 2 duplicate

    def test_headers_present_in_csv_response(self, api_client: TestClient):
        payload = _minimal_pipeline_result().model_dump()
        resp = api_client.post("/api/v1/member1/export-findings-csv", json=payload)
        reader = csv.DictReader(io.StringIO(resp.text))
        for col in ALL_COLUMNS:
            assert col in (reader.fieldnames or []), f"Missing header column: {col}"

    def test_empty_findings_returns_200_with_header_only(self, api_client: TestClient):
        payload = _empty_pipeline_result().model_dump()
        resp = api_client.post("/api/v1/member1/export-findings-csv", json=payload)
        assert resp.status_code == 200
        reader = csv.DictReader(io.StringIO(resp.text))
        rows = list(reader)
        assert rows == []

    def test_invalid_payload_returns_422(self, api_client: TestClient):
        """A payload missing required fields must produce HTTP 422 Unprocessable Entity."""
        resp = api_client.post(
            "/api/v1/member1/export-findings-csv",
            json={"application_id": "MISSING-MOST-FIELDS"},
        )
        assert resp.status_code == 422

    def test_completely_wrong_payload_returns_422(self, api_client: TestClient):
        resp = api_client.post(
            "/api/v1/member1/export-findings-csv",
            json={"not_a_field": True},
        )
        assert resp.status_code == 422

    def test_institution_isolation_is_caller_responsibility(self, api_client: TestClient):
        """Demonstrates that the endpoint trusts the payload's application_id.

        Institution isolation MUST be enforced by Member 2's authentication and
        authorisation middleware before routing to this endpoint – consistent with
        how /process-application is guarded.  This test documents that boundary:
        two payloads with different application_ids produce independent, separate
        CSV reports with the correct application_id embedded in every row.
        """
        payload_a = _minimal_pipeline_result(application_id="INST-A-BATCH-01").model_dump()
        payload_b = _minimal_pipeline_result(application_id="INST-B-BATCH-99").model_dump()

        resp_a = api_client.post("/api/v1/member1/export-findings-csv", json=payload_a)
        resp_b = api_client.post("/api/v1/member1/export-findings-csv", json=payload_b)

        assert resp_a.status_code == 200
        assert resp_b.status_code == 200

        rows_a = list(csv.DictReader(io.StringIO(resp_a.text)))
        rows_b = list(csv.DictReader(io.StringIO(resp_b.text)))

        # Verify no cross-contamination of application_id
        for row in rows_a:
            assert row["application_id"] == "INST-A-BATCH-01", (
                f"Institution A report leaked institution B id: {row['application_id']}"
            )
        for row in rows_b:
            assert row["application_id"] == "INST-B-BATCH-99", (
                f"Institution B report leaked institution A id: {row['application_id']}"
            )

    def test_formula_injection_sanitised_in_response(self, api_client: TestClient):
        """Formula prefixes injected via deficiency_reason must be escaped in the CSV."""
        result = _minimal_pipeline_result()
        result.rule_evaluations[0].deficiency_reason = "=HYPERLINK(\"http://evil.example\",\"click\")"
        payload = result.model_dump()
        resp = api_client.post("/api/v1/member1/export-findings-csv", json=payload)
        assert resp.status_code == 200
        reader = csv.DictReader(io.StringIO(resp.text))
        reg_rows = [r for r in reader if r["finding_type"] == "REGULATORY_RULE"]
        assert len(reg_rows) == 1
        assert reg_rows[0]["deficiency_reason"].startswith("'"), (
            f"Formula injection not sanitised: {reg_rows[0]['deficiency_reason']!r}"
        )

    def test_path_traversal_in_application_id_is_safe(self, api_client: TestClient):
        """application_id with path separators must not leak to filesystem or headers."""
        result = _minimal_pipeline_result(application_id="../../etc/passwd")
        payload = result.model_dump()
        resp = api_client.post("/api/v1/member1/export-findings-csv", json=payload)
        assert resp.status_code == 200
        cd = resp.headers.get("content-disposition", "")
        # Slashes must have been replaced with underscores
        assert "etc" in cd
        assert "/" not in cd.split("filename=")[1]
        assert "\\" not in cd.split("filename=")[1]
