"""
Reports API Router.
Handles CSV export of validation errors, batch findings, and data quality summaries.
Enforces server-side RBAC and strict institution-level data isolation.
"""

import csv
import io
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
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

    output = io.StringIO()
    writer = csv.writer(output)

    if report_type == "quality_summary":
        # Export quality scores across batches
        query = db.query(ImportBatch)
        if target_inst:
            query = query.filter(ImportBatch.institution_id == target_inst)
        if batch_id:
            query = query.filter(ImportBatch.id == batch_id)

        batches = query.order_by(ImportBatch.created_at.desc()).all()
        writer.writerow([
            "batch_id", "institution_id", "academic_year", "version", "status",
            "total_records", "overall_quality_score", "quality_grade",
            "completeness_score", "validity_score", "consistency_score", "uniqueness_score"
        ])

        for b in batches:
            score = calculate_batch_quality_score(db, b)
            writer.writerow([
                b.id, b.institution_id, b.academic_year, b.version, b.status.value,
                score.total_records, score.overall_score, score.grade,
                score.completeness.score, score.validity.score, score.consistency.score, score.uniqueness.score
            ])

        filename = f"quality_summary_{target_inst or 'all'}.csv"

    else:
        # Default: Export row findings
        query = db.query(ValidationFinding).join(ImportBatch)
        if target_inst:
            query = query.filter(ImportBatch.institution_id == target_inst)
        if batch_id:
            query = query.filter(ValidationFinding.batch_id == batch_id)

        findings = query.order_by(ValidationFinding.batch_id, ValidationFinding.row_number).all()

        writer.writerow([
            "finding_id", "batch_id", "row_number", "field_name", "rule_code",
            "severity", "status", "message", "expected_value", "actual_value", "suggested_action"
        ])

        for f in findings:
            writer.writerow([
                f.id, f.batch_id, f.row_number or "", f.field_name or "", f.rule_code,
                f.severity.value, f.status.value, f.message,
                f.expected_value or "", f.actual_value or "", f.suggested_action or ""
            ])

        filename = f"findings_report_{target_inst or batch_id or 'all'}.csv"

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

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
