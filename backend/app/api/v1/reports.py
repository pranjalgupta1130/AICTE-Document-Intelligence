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
from backend.app.models.enums import AuditAction, FindingSeverity, FindingStatus, UserRole
from backend.app.models.user import User
from backend.app.models.validation import ValidationFinding
from backend.app.schemas.common import PaginatedList
from backend.app.schemas.imports import AuditEventRead, ValidationFindingRead
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

@router.get("/export", summary="Export CSV validation findings, data quality report, or audit trail")
def export_report_csv(
    batch_id: Optional[str] = Query(None, description="Export findings for specific batch"),
    institution_id: Optional[str] = Query(None, description="Filter by institution (strictly enforced)"),
    report_type: str = Query("findings", description="Report type: 'findings', 'quality_summary', or 'audit_logs'"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate and stream a CSV report.
    - 'findings': Export row-level validation findings, rule codes, severity, and suggested remediation.
    - 'quality_summary': Export overall data quality scores and component dimensions.
    - 'audit_logs': Export immutable system audit event trail.
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

        elif report_type == "audit_logs":
            # Export system audit event trail
            query = db.query(AuditEvent)
            if target_inst:
                query = query.filter(AuditEvent.institution_id == target_inst)
            if batch_id:
                query = query.filter(
                    (AuditEvent.object_id == batch_id) |
                    (AuditEvent.details.contains(batch_id))
                )

            events = query.order_by(AuditEvent.timestamp.desc()).all()
            header_buf = io.StringIO()
            header_writer = csv.writer(header_buf)
            header_writer.writerow([
                "event_id", "timestamp", "actor_email", "actor_role", "institution_id",
                "action", "object_type", "object_id", "outcome", "details"
            ])
            yield header_buf.getvalue()

            for e in events:
                row_buf = io.StringIO()
                row_writer = csv.writer(row_buf)
                row_writer.writerow([
                    sanitize_csv_cell(e.id),
                    sanitize_csv_cell(e.timestamp.isoformat() if e.timestamp else ""),
                    sanitize_csv_cell(e.actor_email),
                    sanitize_csv_cell(e.actor_role),
                    sanitize_csv_cell(e.institution_id or ""),
                    sanitize_csv_cell(e.action.value if hasattr(e.action, "value") else str(e.action)),
                    sanitize_csv_cell(e.object_type),
                    sanitize_csv_cell(e.object_id or ""),
                    sanitize_csv_cell(e.outcome),
                    sanitize_csv_cell(e.details or "")
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
        f"audit_logs_{target_inst or 'all'}.csv"
        if report_type == "audit_logs"
        else f"quality_summary_{target_inst or 'all'}.csv"
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

@router.get("/audit-logs", response_model=PaginatedList[AuditEventRead], summary="List paginated system audit events with server-side filters")
def list_audit_logs(
    institution_id: Optional[str] = Query(None, description="Filter by institution (strictly enforced)"),
    action: Optional[AuditAction] = Query(None, description="Filter by audit action type"),
    actor_email: Optional[str] = Query(None, description="Filter by actor email"),
    object_type: Optional[str] = Query(None, description="Filter by object type"),
    object_id: Optional[str] = Query(None, description="Filter by object ID"),
    outcome: Optional[str] = Query(None, description="Filter by outcome (e.g. SUCCESS, FAILURE)"),
    search: Optional[str] = Query(None, description="Text search in details, actor, or object ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve paginated immutable audit events.
    - AICTE_ADMIN and DEMO_ADMIN can view audit logs across all institutions or filter by institution.
    - INSTITUTION_ADMIN and INSTITUTION_OPERATOR are strictly isolated to their own institution events.
    """
    if current_user.role == UserRole.EXTERNAL_VERIFIER:
        raise PermissionDeniedError("External verifiers cannot access general audit logs.")

    target_inst = enforce_institution_scope(current_user, institution_id)

    query = db.query(AuditEvent)
    if target_inst:
        query = query.filter(AuditEvent.institution_id == target_inst)

    if action:
        query = query.filter(AuditEvent.action == action)
    if actor_email:
        query = query.filter(AuditEvent.actor_email.ilike(f"%{actor_email.strip()}%"))
    if object_type:
        query = query.filter(AuditEvent.object_type == object_type)
    if object_id:
        query = query.filter(AuditEvent.object_id == object_id)
    if outcome:
        query = query.filter(AuditEvent.outcome == outcome)
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            (AuditEvent.details.ilike(search_term)) |
            (AuditEvent.actor_email.ilike(search_term)) |
            (AuditEvent.object_id.ilike(search_term)) |
            (AuditEvent.id.ilike(search_term))
        )

    total = query.count()
    events = query.order_by(AuditEvent.timestamp.desc()).offset(offset).limit(limit).all()

    items = [AuditEventRead.model_validate(e) for e in events]
    return PaginatedList[AuditEventRead](items=items, total=total)

@router.get("/findings", response_model=PaginatedList[ValidationFindingRead], summary="List paginated validation findings with institution scoping and filters")
def list_findings(
    institution_id: Optional[str] = Query(None, description="Filter by institution (strictly enforced)"),
    batch_id: Optional[str] = Query(None, description="Filter by batch ID"),
    academic_year: Optional[str] = Query(None, description="Filter by academic year"),
    severity: Optional[FindingSeverity] = Query(None, description="Filter by finding severity"),
    status: Optional[FindingStatus] = Query(None, description="Filter by finding status (OPEN, RESOLVED, DISMISSED)"),
    rule_code: Optional[str] = Query(None, description="Filter by rule code prefix or code"),
    search: Optional[str] = Query(None, description="Text search in message, field, actual value, or rule code"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve paginated validation findings across batches or for a specific batch.
    - AICTE_ADMIN and DEMO_ADMIN can view all findings or filter by institution.
    - Institution users can only view findings for batches belonging to their own institution.
    """
    target_inst = enforce_institution_scope(current_user, institution_id)

    query = db.query(ValidationFinding).join(ImportBatch)
    if target_inst:
        query = query.filter(ImportBatch.institution_id == target_inst)
    if batch_id:
        query = query.filter(ValidationFinding.batch_id == batch_id)
    if academic_year:
        query = query.filter(ImportBatch.academic_year == academic_year)
    if severity:
        query = query.filter(ValidationFinding.severity == severity)
    if status:
        query = query.filter(ValidationFinding.status == status)
    if rule_code:
        query = query.filter(ValidationFinding.rule_code.ilike(f"{rule_code.strip()}%"))
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            (ValidationFinding.message.ilike(search_term)) |
            (ValidationFinding.rule_code.ilike(search_term)) |
            (ValidationFinding.field_name.ilike(search_term)) |
            (ValidationFinding.actual_value.ilike(search_term)) |
            (ValidationFinding.record_id.ilike(search_term))
        )

    total = query.count()
    findings = query.order_by(
        ValidationFinding.batch_id.desc(),
        ValidationFinding.row_number.asc().nullslast(),
        ValidationFinding.id.asc()
    ).offset(offset).limit(limit).all()

    items = [ValidationFindingRead.model_validate(f) for f in findings]
    return PaginatedList[ValidationFindingRead](items=items, total=total)
