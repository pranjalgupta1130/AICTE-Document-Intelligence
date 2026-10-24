from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.core.errors import NotFoundError
from backend.app.core.permissions import get_current_user, enforce_institution_scope
from backend.app.db.session import get_db
from backend.app.models.batch import ImportBatch
from backend.app.models.enums import BatchStatus, FindingSeverity
from backend.app.models.match import MatchCandidate
from backend.app.models.student import StudentRecord
from backend.app.models.user import User
from backend.app.models.validation import ValidationFinding
from backend.app.schemas.common import PaginatedList
from backend.app.schemas.imports import BatchRead, ValidationFindingRead
from backend.app.schemas.validation import BatchValidationResponse, MatchCandidateRead
from backend.app.schemas.workflows import BatchSubmitRequest, BatchSubmitResponse

router = APIRouter(prefix="/batches", tags=["Batches"])

@router.get("", response_model=PaginatedList[BatchRead], summary="List import batches scoped by role and institution")
def list_batches(
    institution_id: Optional[str] = Query(None, description="Filter by institution ID (enforced against caller)"),
    academic_year: Optional[str] = Query(None, description="Filter by academic year"),
    status: Optional[BatchStatus] = Query(None, description="Filter by batch status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List import batches with counts, lineage, and lifecycle status.
    Institution users can ONLY inspect batches belonging to their own institution.
    """
    scoped_inst_id = enforce_institution_scope(current_user, institution_id)

    query = db.query(ImportBatch)
    if scoped_inst_id:
        query = query.filter(ImportBatch.institution_id == scoped_inst_id)
    if academic_year:
        query = query.filter(ImportBatch.academic_year == academic_year)
    if status:
        query = query.filter(ImportBatch.status == status)

    total = query.count()
    batches = query.order_by(ImportBatch.created_at.desc()).offset(offset).limit(limit).all()

    items = [BatchRead.model_validate(b) for b in batches]
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

    return BatchRead.model_validate(batch)

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
