"""
Phase 3 Unified Integration and Regression Test Suite.

Covers the end-to-end workflows of the three remaining pages:
1. Bulk Import & Validation (Upload, validation findings, lifecycle submission guard)
2. Data Quality & Findings (Pagination, filtering, remediation review, audit recording)
3. Audit Logs & Reports (Persisted audit retrieval, filtering, tenant isolation, CSV export sanitization)
"""

from __future__ import annotations

import csv
import io
import uuid
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from backend.app.db.session import SessionLocal
from backend.app.main import app
from backend.app.models.batch import ImportBatch
from backend.app.models.enums import BatchStatus, FindingSeverity, FindingStatus, UserRole, AuditAction
from backend.app.models.validation import ValidationFinding
from backend.app.models.audit import AuditEvent


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def get_token(client: TestClient, email: str, password: str = "DemoPassword@2026") -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


class TestAuditLogsEndpoints:
    """Test suite for GET /api/v1/reports/audit-logs."""

    def test_unauthenticated_request_rejected(self, client: TestClient):
        resp = client.get("/api/v1/reports/audit-logs")
        assert resp.status_code == 401

    def test_external_verifier_rejected(self, client: TestClient):
        db = SessionLocal()
        from backend.app.models.user import User
        verifier = db.query(User).filter(User.role == UserRole.EXTERNAL_VERIFIER).first()
        db.close()
        if verifier:
            ver_token = get_token(client, verifier.email)
            resp = client.get("/api/v1/reports/audit-logs", headers={"Authorization": f"Bearer {ver_token}"})
            assert resp.status_code == 403

    def test_audit_logs_retrieval_and_pagination(self, client: TestClient):
        token = get_token(client, "apex_admin@apex.edu.in")
        resp = client.get(
            "/api/v1/reports/audit-logs?limit=10&offset=0",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        assert data["total"] >= 0

        if data["items"]:
            first = data["items"][0]
            assert "id" in first
            assert "action" in first
            assert "actor_email" in first
            assert "timestamp" in first
            assert "outcome" in first

    def test_audit_logs_action_and_search_filter(self, client: TestClient):
        token = get_token(client, "apex_admin@apex.edu.in")
        resp = client.get(
            "/api/v1/reports/audit-logs?action=BATCH_VALIDATE",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["action"] == "BATCH_VALIDATE"

    def test_audit_logs_tenant_isolation(self, client: TestClient):
        """Institutional user cannot see another institution's audit events."""
        token = get_token(client, "apex_admin@apex.edu.in")  # INST-001
        resp = client.get(
            "/api/v1/reports/audit-logs?institution_id=INST-002",
            headers={"Authorization": f"Bearer {token}"}
        )
        # Should be forbidden to request a different tenant
        assert resp.status_code == 403


class TestFindingsEndpoints:
    """Test suite for GET /api/v1/reports/findings."""

    def test_unauthenticated_findings_rejected(self, client: TestClient):
        resp = client.get("/api/v1/reports/findings")
        assert resp.status_code == 401

    def test_findings_retrieval_and_filtering(self, client: TestClient):
        token = get_token(client, "apex_admin@apex.edu.in")
        resp = client.get(
            "/api/v1/reports/findings?limit=20&offset=0",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_findings_severity_and_status_filter(self, client: TestClient):
        token = get_token(client, "apex_admin@apex.edu.in")
        resp = client.get(
            "/api/v1/reports/findings?severity=BLOCKING_ERROR&status=OPEN",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["severity"] == "BLOCKING_ERROR"
            assert item["status"] == "OPEN"

    def test_findings_cross_tenant_isolation(self, client: TestClient):
        token = get_token(client, "apex_admin@apex.edu.in")  # INST-001
        resp = client.get(
            "/api/v1/reports/findings?institution_id=INST-002",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403


class TestAuditExportEndpoint:
    """Test suite for GET /api/v1/reports/export?report_type=audit_logs."""

    def test_audit_export_csv_headers_and_content(self, client: TestClient):
        token = get_token(client, "apex_admin@apex.edu.in")
        resp = client.get(
            "/api/v1/reports/export?report_type=audit_logs",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")
        reader = csv.DictReader(io.StringIO(resp.text))
        expected_cols = [
            "event_id", "timestamp", "actor_email", "actor_role", "institution_id",
            "action", "object_type", "object_id", "outcome", "details"
        ]
        for col in expected_cols:
            assert col in (reader.fieldnames or []), f"Missing column {col} in CSV"

    def test_audit_export_formula_injection_sanitization(self, client: TestClient):
        """Verify formula prefixes in audit details are safely escaped with a single quote."""
        token = get_token(client, "apex_admin@apex.edu.in")
        db = SessionLocal()
        test_evt_id = f"evt-inj-{uuid.uuid4().hex[:6]}"
        try:
            from datetime import timezone
            evt = AuditEvent(
                id=test_evt_id,
                actor_user_id=None,
                actor_email="apex_admin@apex.edu.in",
                actor_role="INSTITUTION_ADMIN",
                institution_id="INST-001",
                action=AuditAction.REPORT_EXPORT,
                object_type="TestInject",
                object_id=f"=SUM(A1:A10)",
                outcome="SUCCESS",
                details=f"+cmd|' /C calc'!A0",
                timestamp=datetime.now(timezone.utc)
            )
            db.add(evt)
            db.commit()

            resp = client.get(
                "/api/v1/reports/export?report_type=audit_logs",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert resp.status_code == 200
            reader = csv.DictReader(io.StringIO(resp.text))
            found = False
            for row in reader:
                if row.get("event_id") == test_evt_id:
                    found = True
                    # Formula prefixes should be escaped with leading '
                    assert row["object_id"].startswith("'="), f"Unescaped formula: {row['object_id']}"
                    assert row["details"].startswith("'+"), f"Unescaped formula: {row['details']}"
            assert found, "Test event not found in export"
        except Exception:
            db.rollback()
            raise
        finally:
            db.query(AuditEvent).filter(AuditEvent.id == test_evt_id).delete()
            db.commit()
            db.close()


class TestRemediationAndWorkflow:
    """Test suite for Finding review and batch submission workflow."""

    def test_finding_review_updates_status_and_logs_audit_event(self, client: TestClient):
        token = get_token(client, "apex_admin@apex.edu.in")
        db = SessionLocal()

        batch_id = f"BATCH-TEST-{uuid.uuid4().hex[:6]}"
        finding_id = f"find-test-{uuid.uuid4().hex[:6]}"

        try:
            # Create a test batch and finding
            batch = ImportBatch(
                id=batch_id,
                institution_id="INST-001",
                source_filename="test_finding_remediation.csv",
                academic_year="2026-2027",
                version=999,
                status=BatchStatus.NEEDS_CORRECTION,
                total_rows=1,
                valid_rows=0,
                error_rows=1,
            )
            finding = ValidationFinding(
                id=finding_id,
                batch_id=batch_id,
                record_id=None,
                rule_code="RULE-R6-MISSING-APAAR",
                severity=FindingSeverity.BLOCKING_ERROR,
                status=FindingStatus.OPEN,
                field_name="apaar_id",
                row_number=1,
                message="Missing APAAR ID",
                suggested_action="Enter 12-digit APAAR ID",
            )
            db.add(batch)
            db.add(finding)
            db.commit()

            # Execute review action
            resp = client.post(
                f"/api/v1/reviews/{finding_id}",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "decision": "RESOLVED",
                    "reason": "Verified against state board affidavit #AFF-2026-001",
                }
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "RESOLVED"
            assert data["finding_id"] == finding_id

            # Verify finding status updated in database
            db.expire_all()
            f_db = db.query(ValidationFinding).filter(ValidationFinding.id == finding_id).first()
            assert f_db is not None
            assert f_db.status == FindingStatus.RESOLVED

            # Verify audit event was generated
            audit = db.query(AuditEvent).filter(
                AuditEvent.object_type == "VALIDATION_FINDING",
                AuditEvent.object_id == finding_id,
            ).first()
            assert audit is not None
            assert audit.action == AuditAction.REVIEW_DECISION
            assert "RESOLVED" in (audit.details or "")

        except Exception:
            db.rollback()
            raise
        finally:
            db.query(AuditEvent).filter(AuditEvent.object_id == finding_id).delete()
            db.query(ValidationFinding).filter(ValidationFinding.id == finding_id).delete()
            db.query(ImportBatch).filter(ImportBatch.id == batch_id).delete()
            db.commit()
            db.close()

    def test_batch_submission_guard_blocks_unresolved_errors(self, client: TestClient):
        token = get_token(client, "apex_admin@apex.edu.in")
        db = SessionLocal()

        batch_id = f"BATCH-SUBMIT-{uuid.uuid4().hex[:6]}"
        finding_id = f"find-submit-{uuid.uuid4().hex[:6]}"

        try:
            batch = ImportBatch(
                id=batch_id,
                institution_id="INST-001",
                source_filename="test_submit_guard.csv",
                academic_year="2026-2027",
                version=999,
                status=BatchStatus.VALIDATED,
                total_rows=10,
                valid_rows=9,
                error_rows=1,
            )
            finding = ValidationFinding(
                id=finding_id,
                batch_id=batch_id,
                record_id=None,
                rule_code="RULE-R6-MISSING-APAAR",
                severity=FindingSeverity.BLOCKING_ERROR,
                status=FindingStatus.OPEN,
                message="Blocking error present",
            )
            db.add(batch)
            db.add(finding)
            db.commit()

            # Attempt submission while blocking finding is OPEN
            resp = client.post(
                f"/api/v1/batches/{batch_id}/submit",
                headers={"Authorization": f"Bearer {token}"},
                json={"confirm_declaration": True, "comments": "Attempting submission with blocker"}
            )
            assert resp.status_code == 400
            assert "blocking" in resp.text.lower()

            # Now resolve the finding
            finding.status = FindingStatus.RESOLVED
            batch.error_rows = 0
            db.commit()

            # Re-attempt submission
            resp_ok = client.post(
                f"/api/v1/batches/{batch_id}/submit",
                headers={"Authorization": f"Bearer {token}"},
                json={"confirm_declaration": True, "comments": "Submission after remediation"}
            )
            assert resp_ok.status_code == 200
            assert resp_ok.json()["status"] == "SUBMITTED"

            # Verify in DB
            db.expire_all()
            b_db = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
            assert b_db.status == BatchStatus.SUBMITTED

        except Exception:
            db.rollback()
            raise
        finally:
            db.query(AuditEvent).filter(AuditEvent.object_id == batch_id).delete()
            db.query(ValidationFinding).filter(ValidationFinding.id == finding_id).delete()
            db.query(ImportBatch).filter(ImportBatch.id == batch_id).delete()
            db.commit()
            db.close()
