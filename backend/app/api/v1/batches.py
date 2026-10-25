import os
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.errors import AppException, NotFoundError, PermissionDeniedError
from backend.app.core.permissions import get_current_user, enforce_institution_scope
from backend.app.db.session import get_db
from backend.app.models.audit import AuditEvent
from backend.app.models.batch import ImportBatch
from backend.app.models.enums import AuditAction, BatchStatus, FindingSeverity, UserRole
from backend.app.models.match import MatchCandidate
from backend.app.models.student import StudentRecord
from backend.app.models.user import User
from backend.app.models.validation import ValidationFinding
from backend.app.schemas.common import PaginatedList
from backend.app.schemas.imports import BatchRead, StudentRecordRead, ValidationFindingRead
from backend.app.schemas.validation import BatchValidationResponse, MatchCandidateRead
from backend.app.schemas.workflows import BatchSubmitRequest, BatchSubmitResponse, BatchReviewRequest, BatchReviewResponse

router = APIRouter(prefix="/batches", tags=["Batches"])

@router.delete("/{batch_id}", summary="Safely delete an unsubmitted import batch and associated records")
def delete_batch(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Safely delete an unsubmitted import batch.
    - Only INSTITUTION_ADMIN, AICTE_ADMIN, or DEMO_ADMIN are permitted.
    - Strict institutional tenant scoping enforced.
    - Rejects deletion if batch is already SUBMITTED, UNDER_REVIEW, or ACCEPTED.
    - Safely removes associated student records, validation findings, and staged match candidates.
    - Records an immutable audit log entry.
    """
    if current_user.role not in (UserRole.INSTITUTION_ADMIN, UserRole.AICTE_ADMIN, UserRole.DEMO_ADMIN):
        raise PermissionDeniedError(f"Role '{current_user.role.value}' is not authorized to delete batches.")

    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch:
        raise NotFoundError(f"ImportBatch '{batch_id}' was not found.")

    # Strict tenant isolation
    enforce_institution_scope(current_user, batch.institution_id)

    # Pre-submission lifecycle guard: never allow deletion of officially submitted or accepted batches
    if batch.status in (BatchStatus.SUBMITTED, BatchStatus.UNDER_REVIEW, BatchStatus.ACCEPTED):
        raise AppException(
            code="PROTECTED_BATCH_STATUS",
            message=f"Cannot delete batch '{batch_id}' in protected status '{batch.status.value}'. Submitted or accepted batches are locked for compliance.",
            status_code=400
        )

    # 1. Clean up any match candidates referencing students in this batch
    batch_record_ids = [s.id for s in db.query(StudentRecord.id).filter(StudentRecord.batch_id == batch_id).all()]
    deleted_matches_count = 0
    if batch_record_ids:
        deleted_matches_count = db.query(MatchCandidate).filter(
            (MatchCandidate.record_a_id.in_(batch_record_ids)) |
            (MatchCandidate.record_b_id.in_(batch_record_ids))
        ).delete(synchronize_session=False)

    total_records = len(batch_record_ids)
    findings_count = db.query(ValidationFinding).filter(ValidationFinding.batch_id == batch_id).count()
    source_filename = batch.source_filename
    inst_id = batch.institution_id

    # 2. Record immutable audit log
    audit = AuditEvent(
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role.value,
        institution_id=inst_id,
        action=AuditAction.BATCH_DELETE,
        object_type="IMPORT_BATCH",
        object_id=batch_id,
        outcome="SUCCESS",
        details=f"Deleted batch '{batch_id}' ({source_filename}) with {total_records} student records, {findings_count} findings, {deleted_matches_count} match candidates."
    )
    db.add(audit)

    # 3. Clean up retained original file if present
    if batch.storage_path:
        try:
            storage_dir = os.path.abspath(settings.UPLOAD_STORAGE_DIR)
            file_disk_path = os.path.join(storage_dir, os.path.basename(batch.storage_path))
            if os.path.exists(file_disk_path) and os.path.isfile(file_disk_path):
                os.remove(file_disk_path)
        except Exception:
            pass

    # 4. Delete batch (triggers SQLAlchemy cascade delete-orphan on student_records and findings)
    db.delete(batch)
    db.commit()

    return {
        "success": True,
        "message": f"Batch '{batch_id}' and all associated records were successfully deleted.",
        "batch_id": batch_id,
        "deleted_records": total_records,
        "deleted_findings": findings_count,
        "deleted_matches": deleted_matches_count
    }

def _to_batch_read(batch: ImportBatch) -> BatchRead:
    has_file = False
    if batch.storage_path:
        storage_dir = os.path.abspath(settings.UPLOAD_STORAGE_DIR)
        file_path = os.path.join(storage_dir, os.path.basename(batch.storage_path))
        has_file = os.path.exists(file_path) and os.path.isfile(file_path)

    inst_name = batch.institution.name if batch.institution else None
    uploader_email = batch.uploader.email if batch.uploader else None

    return BatchRead(
        id=batch.id,
        institution_id=batch.institution_id,
        institution_name=inst_name,
        uploader_user_id=batch.uploader_user_id,
        uploader_email=uploader_email,
        source_filename=batch.source_filename,
        academic_year=batch.academic_year,
        version=batch.version,
        status=batch.status,
        total_rows=batch.total_rows,
        valid_rows=batch.valid_rows,
        error_rows=batch.error_rows,
        warning_rows=batch.warning_rows,
        has_original_file=has_file,
        file_size_bytes=batch.file_size_bytes,
        created_at=batch.created_at,
        updated_at=batch.updated_at
    )

@router.get("", response_model=PaginatedList[BatchRead], summary="List import batches scoped by role and institution")
def list_batches(
    institution_id: Optional[str] = Query(None, description="Filter by institution ID (enforced against caller)"),
    academic_year: Optional[str] = Query(None, description="Filter by academic year"),
    status: Optional[BatchStatus] = Query(None, description="Filter by batch status"),
    search: Optional[str] = Query(None, description="Search by batch ID or source filename"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List import batches with counts, lineage, and lifecycle status.
    Institution users can ONLY inspect batches belonging to their own institution.
    Supports filtering by institution, academic year, status, and search query.
    """
    scoped_inst_id = enforce_institution_scope(current_user, institution_id)

    query = db.query(ImportBatch)
    if scoped_inst_id:
        query = query.filter(ImportBatch.institution_id == scoped_inst_id)
    if academic_year:
        query = query.filter(ImportBatch.academic_year == academic_year)
    if status:
        query = query.filter(ImportBatch.status == status)
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            (ImportBatch.id.ilike(search_term)) |
            (ImportBatch.source_filename.ilike(search_term))
        )

    total = query.count()
    batches = query.order_by(ImportBatch.created_at.desc()).offset(offset).limit(limit).all()

    items = [_to_batch_read(b) for b in batches]
    return PaginatedList[BatchRead](items=items, total=total)

@router.get("/{batch_id}", response_model=BatchRead, summary="Get batch status, counts, and lineage")
def get_batch(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve specific batch details and verification state.
    Enforces strict institution isolation.
    """
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch:
        raise NotFoundError(f"ImportBatch '{batch_id}' was not found.")

    # Enforce institution isolation on target batch
    enforce_institution_scope(current_user, batch.institution_id)

    return _to_batch_read(batch)

@router.get("/{batch_id}/download", summary="Download the original uploaded spreadsheet/dataset")
def download_original_file(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Securely download original uploaded file if retained on server.
    - Requires authenticated caller authorized for the batch's institution.
    - Path traversal protected via basename sanitization.
    - Emits immutable audit log entry.
    """
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch:
        raise NotFoundError(f"ImportBatch '{batch_id}' was not found.")

    enforce_institution_scope(current_user, batch.institution_id)

    if current_user.role == UserRole.EXTERNAL_VERIFIER:
        raise PermissionDeniedError("External verifiers cannot download raw datasets.")

    if not batch.storage_path:
        raise NotFoundError("Original file unavailable — this document was not retained by the system.")

    safe_name = os.path.basename(batch.storage_path)
    storage_dir = os.path.abspath(settings.UPLOAD_STORAGE_DIR)
    full_path = os.path.abspath(os.path.join(storage_dir, safe_name))

    # Path traversal protection
    if not full_path.startswith(storage_dir):
        raise PermissionDeniedError("Access to the requested file path is restricted.")

    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise NotFoundError("Original file unavailable — this document was not retained by the system.")

    media_type = "text/csv"
    if batch.source_filename.lower().endswith(".xlsx"):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    # Audit log
    audit = AuditEvent(
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_role=getattr(current_user.role, "value", str(current_user.role)),
        institution_id=batch.institution_id,
        action=AuditAction.REPORT_EXPORT,
        object_type="ORIGINAL_DATASET",
        object_id=batch_id,
        outcome="SUCCESS",
        details=f"Downloaded original dataset: {batch.source_filename}"
    )
    db.add(audit)
    db.commit()

    def iter_file():
        with open(full_path, "rb") as f:
            while chunk := f.read(64 * 1024):
                yield chunk

    return StreamingResponse(
        iter_file(),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{batch.source_filename}"'}
    )

@router.get("/{batch_id}/records", response_model=PaginatedList[StudentRecordRead], summary="List imported student records for a batch")
def get_batch_records(
    batch_id: str,
    search: Optional[str] = Query(None, description="Search by institution student ID or student name"),
    programme_id: Optional[str] = Query(None, description="Filter by programme ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve paginated student records imported under this batch.
    Sensitive APAAR IDs are masked for non-administrative roles according to access policy.
    """
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch:
        raise NotFoundError(f"ImportBatch '{batch_id}' was not found.")

    enforce_institution_scope(current_user, batch.institution_id)

    query = db.query(StudentRecord).filter(StudentRecord.batch_id == batch_id)
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            (StudentRecord.institution_student_id.ilike(search_term)) |
            (StudentRecord.student_name.ilike(search_term))
        )
    if programme_id:
        query = query.filter(StudentRecord.programme_id == programme_id)

    total = query.count()
    records = query.order_by(StudentRecord.source_row_number.asc().nullslast(), StudentRecord.id.asc()).offset(offset).limit(limit).all()

    # Mask APAAR ID if caller is not an administrator or verifier with full access
    items = []
    for r in records:
        masked_apaar = r.apaar_id
        if masked_apaar and current_user.role not in (UserRole.AICTE_ADMIN, UserRole.DEMO_ADMIN, UserRole.INSTITUTION_ADMIN):
            # Mask middle characters: e.g. 9082-XXXX-8821
            if len(masked_apaar) >= 12:
                masked_apaar = f"{masked_apaar[:4]}-XXXX-{masked_apaar[-4:]}"
        items.append(StudentRecordRead(
            id=r.id,
            batch_id=r.batch_id,
            institution_id=r.institution_id,
            programme_id=r.programme_id,
            apaar_id=masked_apaar,
            institution_student_id=r.institution_student_id,
            student_name=r.student_name,
            academic_year=r.academic_year,
            enrolment_status=r.enrolment_status.value if hasattr(r.enrolment_status, "value") else str(r.enrolment_status),
            seat_type=r.seat_type.value if hasattr(r.seat_type, "value") else str(r.seat_type),
            is_nri=r.is_nri,
            is_oci=r.is_oci,
            is_fn=r.is_fn,
            source_row_number=r.source_row_number,
            created_at=r.created_at
        ))

    return PaginatedList[StudentRecordRead](items=items, total=total)

@router.get("/{batch_id}/history", summary="Get audit events and lifecycle history for this batch")
def get_batch_history(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve immutable audit events linked to this batch lifecycle.
    """
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch:
        raise NotFoundError(f"ImportBatch '{batch_id}' was not found.")

    enforce_institution_scope(current_user, batch.institution_id)

    events = db.query(AuditEvent).filter(
        AuditEvent.object_type == "IMPORT_BATCH",
        AuditEvent.object_id == batch_id
    ).order_by(AuditEvent.timestamp.desc()).all()

    return [
        {
            "id": e.id,
            "action": e.action.value if hasattr(e.action, "value") else str(e.action),
            "actor_email": e.actor_email,
            "actor_role": e.actor_role,
            "outcome": e.outcome,
            "details": e.details,
            "timestamp": e.timestamp
        }
        for e in events
    ]

@router.get("/{batch_id}/export/records", summary="Export batch student records to CSV")
def export_batch_records_csv(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export all student records of the batch into an injection-sanitized CSV file.
    """
    import csv
    import io
    from backend.app.api.v1.reports import sanitize_csv_cell

    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch:
        raise NotFoundError(f"ImportBatch '{batch_id}' was not found.")

    enforce_institution_scope(current_user, batch.institution_id)

    if current_user.role == UserRole.EXTERNAL_VERIFIER:
        raise PermissionDeniedError("External verifiers cannot export batch student records.")

    records = db.query(StudentRecord).filter(StudentRecord.batch_id == batch_id).order_by(StudentRecord.source_row_number.asc()).all()

    def generate_records():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "institution_student_id", "student_name", "apaar_id", "programme_id",
            "academic_year", "enrolment_status", "seat_type", "is_nri", "is_oci", "is_fn", "source_row_number"
        ])
        yield buf.getvalue()

        for r in records:
            row_buf = io.StringIO()
            row_writer = csv.writer(row_buf)
            masked_apaar = r.apaar_id
            if masked_apaar and current_user.role not in (UserRole.AICTE_ADMIN, UserRole.DEMO_ADMIN, UserRole.INSTITUTION_ADMIN):
                if len(masked_apaar) >= 12:
                    masked_apaar = f"{masked_apaar[:4]}-XXXX-{masked_apaar[-4:]}"
            row_writer.writerow([
                sanitize_csv_cell(r.institution_student_id),
                sanitize_csv_cell(r.student_name or ""),
                sanitize_csv_cell(masked_apaar or ""),
                sanitize_csv_cell(r.programme_id),
                sanitize_csv_cell(r.academic_year),
                sanitize_csv_cell(r.enrolment_status.value if hasattr(r.enrolment_status, "value") else str(r.enrolment_status)),
                sanitize_csv_cell(r.seat_type.value if hasattr(r.seat_type, "value") else str(r.seat_type)),
                sanitize_csv_cell(r.is_nri),
                sanitize_csv_cell(r.is_oci),
                sanitize_csv_cell(r.is_fn),
                sanitize_csv_cell(r.source_row_number or "")
            ])
            yield row_buf.getvalue()

    filename = f"{batch_id}_records.csv"
    audit = AuditEvent(
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_role=getattr(current_user.role, "value", str(current_user.role)),
        institution_id=batch.institution_id,
        action=AuditAction.REPORT_EXPORT,
        object_type="BATCH_RECORDS",
        object_id=batch_id,
        outcome="SUCCESS",
        details=f"Exported records CSV for batch {batch_id}"
    )
    db.add(audit)
    db.commit()

    return StreamingResponse(
        generate_records(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/{batch_id}/findings", response_model=PaginatedList[ValidationFindingRead], summary="Get paginated row findings for a batch")
def get_batch_findings(
    batch_id: str,
    severity: Optional[FindingSeverity] = Query(None, description="Filter findings by severity"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve explainable validation and parsing findings for a batch.
    """
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch:
        raise NotFoundError(f"ImportBatch '{batch_id}' was not found.")

    # Enforce institution isolation
    enforce_institution_scope(current_user, batch.institution_id)

    query = db.query(ValidationFinding).filter(ValidationFinding.batch_id == batch_id)
    if severity:
        query = query.filter(ValidationFinding.severity == severity)

    total = query.count()
    findings = query.order_by(ValidationFinding.row_number.asc()).offset(offset).limit(limit).all()

    items = [ValidationFindingRead.model_validate(f) for f in findings]
    return PaginatedList[ValidationFindingRead](items=items, total=total)

@router.post("/{batch_id}/validate", response_model=BatchValidationResponse, summary="Execute core validation and intake reconciliation engine")
def validate_batch(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger deterministic validation engine across all student records in the batch.
    Reconciles records against approved AICTE intake, flags syntax/duplicate issues,
    updates batch status to VALIDATED or NEEDS_CORRECTION, and records audit event.
    """
    from backend.app.services.validation_service import execute_batch_validation
    return execute_batch_validation(db=db, batch_id=batch_id, current_user=current_user)

@router.get("/{batch_id}/matches", response_model=PaginatedList[MatchCandidateRead], summary="Get cross-institution candidate duplicates detected for batch")
def get_batch_matches(
    batch_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve candidate duplicates flagged across institutions.
    """
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch:
        raise NotFoundError(f"ImportBatch '{batch_id}' was not found.")

    enforce_institution_scope(current_user, batch.institution_id)

    # Query student record IDs of this batch
    batch_record_ids = db.query(StudentRecord.id).filter(StudentRecord.batch_id == batch_id).scalar_subquery()
    query = db.query(MatchCandidate).filter(
        (MatchCandidate.record_a_id.in_(batch_record_ids)) |
        (MatchCandidate.record_b_id.in_(batch_record_ids))
    )
    total = query.count()
    matches = query.offset(offset).limit(limit).all()
    items = [MatchCandidateRead.model_validate(m) for m in matches]
    return PaginatedList[MatchCandidateRead](items=items, total=total)

@router.post("/{batch_id}/submit", response_model=BatchSubmitResponse, summary="Finalize and submit validated batch")
def submit_batch_endpoint(
    batch_id: str,
    request: BatchSubmitRequest = BatchSubmitRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit a validated batch to lock the data for official AICTE reconciliation.
    Requires batch to be in VALIDATED state with no unresolved blocking errors.
    """
    from backend.app.services.workflow_service import submit_batch
    return submit_batch(db=db, batch_id=batch_id, current_user=current_user, request=request)

@router.post("/{batch_id}/review", response_model=BatchReviewResponse, summary="Review an institutional import batch")
def review_batch_endpoint(
    batch_id: str,
    request: BatchReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Review and update status of an institutional import batch.
    Decisions: UNDER_REVIEW, ACCEPTED, REJECTED, NEEDS_CORRECTION.
    Restricted to AICTE administrators (AICTE_ADMIN, DEMO_ADMIN).
    """
    from backend.app.services.workflow_service import review_batch
    return review_batch(db=db, batch_id=batch_id, current_user=current_user, request=request)

@router.get("/{batch_id}/quality", summary="Get explainable data quality score and component breakdown")
def get_batch_quality_score(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve transparent data quality score (0-100) and dimensional breakdown
    (Completeness, Validity, Consistency, Uniqueness).
    Evaluates dataset hygiene; is NOT a fraud score.
    """
    from backend.app.services.quality_service import calculate_batch_quality_score

    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch:
        raise NotFoundError(f"ImportBatch '{batch_id}' was not found.")

    enforce_institution_scope(current_user, batch.institution_id)
    return calculate_batch_quality_score(db=db, batch=batch)

# ---------------------------------------------------------------------------
# Member 3 Extensions: Anomaly Analytics, Explainable Fuzzy Matching & Deltas
# ---------------------------------------------------------------------------
@router.get("/{batch_id}/anomalies", summary="Get batch anomaly analytics and statistical hygiene report")
def get_batch_anomalies(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve deterministic batch anomaly analytics (missing field spikes, malformed identifier rates,
    duplicate concentration, seat-type distribution anomalies, and quota breaches).
    """
    from backend.app.services.anomaly_service import analyze_batch_anomalies

    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch:
        raise NotFoundError(f"ImportBatch '{batch_id}' was not found.")

    enforce_institution_scope(current_user, batch.institution_id)
    return analyze_batch_anomalies(db=db, batch=batch)

@router.get("/{batch_id}/fuzzy-duplicates", summary="Detect explainable fuzzy duplicate candidates for batch")
def get_batch_fuzzy_duplicates(
    batch_id: str,
    threshold: float = Query(0.75, ge=0.50, le=1.0, description="Similarity confidence threshold"),
    include_cross_institution: bool = Query(True, description="Include active candidates across other institutions"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Evaluate student records in this batch for fuzzy duplicate candidates based on multi-field similarity.
    Returns explainable match attributions without altering student records.
    """
    from backend.app.services.duplicate_fuzzy_service import find_fuzzy_duplicates_for_batch

    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch:
        raise NotFoundError(f"ImportBatch '{batch_id}' was not found.")

    enforce_institution_scope(current_user, batch.institution_id)
    return find_fuzzy_duplicates_for_batch(
        db=db,
        batch_id=batch_id,
        threshold=threshold,
        include_cross_institution=include_cross_institution,
        persist_to_match_candidates=False,
        current_user=current_user
    )

@router.post("/{batch_id}/fuzzy-duplicates/stage", summary="Detect and stage fuzzy duplicate candidates into MatchCandidate review queue")
def stage_batch_fuzzy_duplicates(
    batch_id: str,
    threshold: float = Query(0.75, ge=0.50, le=1.0, description="Similarity confidence threshold"),
    include_cross_institution: bool = Query(True, description="Include active candidates across other institutions"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Detect fuzzy duplicate candidates and stage them into the official MatchCandidate review table
    for AICTE Administrator resolution under the Exception Queue.
    """
    from backend.app.services.duplicate_fuzzy_service import find_fuzzy_duplicates_for_batch

    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch:
        raise NotFoundError(f"ImportBatch '{batch_id}' was not found.")

    enforce_institution_scope(current_user, batch.institution_id)
    return find_fuzzy_duplicates_for_batch(
        db=db,
        batch_id=batch_id,
        threshold=threshold,
        include_cross_institution=include_cross_institution,
        persist_to_match_candidates=True,
        current_user=current_user
    )

@router.get("/{batch_id}/compare/{other_batch_id}", summary="Compare data quality scores between two batch versions")
def compare_batch_quality(
    batch_id: str,
    other_batch_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Compare quality scores between two batches (e.g. initial submission vs revalidated batch after clerical fixes).
    Enforces institution scoping on both batches.
    """
    from backend.app.services.quality_service import calculate_quality_score_improvement

    batch_a = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch_a:
        raise NotFoundError(f"ImportBatch '{batch_id}' was not found.")

    batch_b = db.query(ImportBatch).filter(ImportBatch.id == other_batch_id).first()
    if not batch_b:
        raise NotFoundError(f"ImportBatch '{other_batch_id}' was not found.")

    enforce_institution_scope(current_user, batch_a.institution_id)
    enforce_institution_scope(current_user, batch_b.institution_id)

    return calculate_quality_score_improvement(db=db, batch_before=batch_a, batch_after=batch_b)
