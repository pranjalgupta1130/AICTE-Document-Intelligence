"""
Reports API Router.
Handles CSV export of validation errors, batch findings, and data quality summaries.
Enforces server-side RBAC and strict institution-level data isolation.
"""

import csv
import io
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.core.errors import NotFoundError, PermissionDeniedError
from backend.app.core.permissions import get_current_user, enforce_institution_scope
from backend.app.db.session import get_db
from backend.app.models.audit import AuditEvent
from backend.app.models.batch import ImportBatch
from backend.app.models.enums import AuditAction, FindingSeverity, UserRole
from backend.app.models.user import User
from backend.app.models.validation import ValidationFinding
from backend.app.services.quality_service import calculate_batch_quality_score

# Dangerous formula-injection prefix characters (OWASP CSV Injection standard)
_INJECTION_PREFIXES: tuple = ("=", "+", "-", "@", "|", "%")

def sanitize_csv_cell(val: object) -> str:
    """
    Sanitize a cell value to prevent CSV / Spreadsheet formula injection.
    If the stripped value begins with an injection prefix (=, +, -, @, |, %),
    it is prepended with a single quote (') so that spreadsheet applications
    (Excel, Calc, Google Sheets) treat the content strictly as text.
    Handles leading whitespace and control characters safely without double-escaping.
    """
    if val is None:
        return ""
    s = str(val)
    if not s:
        return ""
    # Check if stripping leading whitespace/control characters reveals a dangerous prefix
    stripped = s.lstrip(" \t\r\n\x00\x0b\x0c")
    if stripped and stripped[0] in _INJECTION_PREFIXES:
        # If not already single-quote escaped
        if not s.startswith("'"):
            return f"'{s}"
    return s

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/export", summary="Export CSV validation findings and data quality report")
def export_report_csv(
    batch_id: Optional[str] = Query(None, description="Export findings for specific batch"),
    institution_id: Optional[str] = Query(None, description="Filter by institution (strictly enforced)"),
    report_type: str = Query("findings", description="Report type: 'findings' or 'quality_summary'"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate and stream a CSV report.
    - 'findings': Export row-level validation findings, rule codes, severity, and suggested remediation.
    - 'quality_summary': Export overall data quality scores and component dimensions.
    Enforces server-side institution isolation and creates an immutable AuditEvent.
    """
    # External verifiers cannot export bulk reports
    if current_user.role == UserRole.EXTERNAL_VERIFIER:
        raise PermissionDeniedError("External verifiers are prohibited from bulk data exports.")

    target_inst = enforce_institution_scope(current_user, institution_id)

    def generate_csv_chunks():
        if report_type == "quality_summary":
            # Export quality scores across batches
            query = db.query(ImportBatch)
            if target_inst:
                query = query.filter(ImportBatch.institution_id == target_inst)
            if batch_id:
                query = query.filter(ImportBatch.id == batch_id)

            batches = query.order_by(ImportBatch.created_at.desc()).all()
            header_buf = io.StringIO()
            header_writer = csv.writer(header_buf)
            header_writer.writerow([
                "batch_id", "institution_id", "academic_year", "version", "status",
                "total_records", "overall_quality_score", "quality_grade",
                "completeness_score", "validity_score", "consistency_score", "uniqueness_score"
            ])
            yield header_buf.getvalue()

            for b in batches:
                row_buf = io.StringIO()
                row_writer = csv.writer(row_buf)
                score = calculate_batch_quality_score(db, b)
                row_writer.writerow([
                    sanitize_csv_cell(b.id),
                    sanitize_csv_cell(b.institution_id),
                    sanitize_csv_cell(b.academic_year),
                    sanitize_csv_cell(b.version),
                    sanitize_csv_cell(b.status.value),
                    sanitize_csv_cell(score.total_records),
                    sanitize_csv_cell(score.overall_score),
                    sanitize_csv_cell(score.grade),
                    sanitize_csv_cell(score.completeness.score),
                    sanitize_csv_cell(score.validity.score),
                    sanitize_csv_cell(score.consistency.score),
                    sanitize_csv_cell(score.uniqueness.score)
                ])
                yield row_buf.getvalue()

        else:
            # Default: Export row findings
            query = db.query(ValidationFinding).join(ImportBatch)
            if target_inst:
                query = query.filter(ImportBatch.institution_id == target_inst)
            if batch_id:
                query = query.filter(ValidationFinding.batch_id == batch_id)

            findings = query.order_by(ValidationFinding.batch_id, ValidationFinding.row_number).all()
            header_buf = io.StringIO()
            header_writer = csv.writer(header_buf)
            header_writer.writerow([
                "finding_id", "batch_id", "row_number", "field_name", "rule_code",
                "severity", "status", "message", "expected_value", "actual_value", "suggested_action"
            ])
            yield header_buf.getvalue()

            for f in findings:
                row_buf = io.StringIO()
                row_writer = csv.writer(row_buf)
                row_writer.writerow([
                    sanitize_csv_cell(f.id),
                    sanitize_csv_cell(f.batch_id),
                    sanitize_csv_cell(f.row_number or ""),
                    sanitize_csv_cell(f.field_name or ""),
                    sanitize_csv_cell(f.rule_code),
                    sanitize_csv_cell(f.severity.value),
                    sanitize_csv_cell(f.status.value),
                    sanitize_csv_cell(f.message),
                    sanitize_csv_cell(f.expected_value or ""),
                    sanitize_csv_cell(f.actual_value or ""),
                    sanitize_csv_cell(f.suggested_action or "")
                ])
                yield row_buf.getvalue()

    filename = (
        f"quality_summary_{target_inst or 'all'}.csv"
        if report_type == "quality_summary"
        else f"findings_report_{target_inst or batch_id or 'all'}.csv"
    )

    # Log export event in audit trail
    audit = AuditEvent(
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role.value,
        institution_id=target_inst,
        action=AuditAction.REPORT_EXPORT,
        object_type="REPORT",
        object_id=batch_id or target_inst or "ALL",
        outcome="SUCCESS",
        details=f"Exported CSV {report_type} report: filename={filename}"
    )
    db.add(audit)
    db.commit()

    return StreamingResponse(
        generate_csv_chunks(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
