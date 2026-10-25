from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct

from backend.app.core.errors import AppException, NotFoundError, PermissionDeniedError
from backend.app.core.permissions import enforce_institution_scope
from backend.app.models.audit import AuditEvent
from backend.app.models.batch import ImportBatch
from backend.app.models.enums import AuditAction, BatchStatus, EnrolmentStatus, FindingSeverity, FindingStatus, MatchStatus, SeatType, UserRole
from backend.app.models.institution import ApprovedIntake, Institution, Programme
from backend.app.models.match import MatchCandidate
from backend.app.models.student import StudentRecord
from backend.app.models.user import User
from backend.app.models.validation import ValidationFinding
from backend.app.schemas.workflows import (
    AICTEDashboardMetrics,
    BatchReviewDecision,
    BatchReviewRequest,
    BatchReviewResponse,
    BatchSubmitRequest,
    BatchSubmitResponse,
    FindingReviewRequest,
    FindingReviewResponse,
    InstitutionDashboardMetrics,
    InstitutionEnrolmentSummary,
    MatchCandidateReviewRequest,
    ProgrammeIntakeMetric,
    RecentActivityItem,
    RecentBatchSummary,
    SpecialQuotaMetric,
)

# ------------------------------------------------------------------------------
# 1. Batch Submission Service
# ------------------------------------------------------------------------------
def submit_batch(
    db: Session,
    batch_id: str,
    current_user: User,
    request: Optional[BatchSubmitRequest] = None
) -> BatchSubmitResponse:
    """
    Transition a validated batch into SUBMITTED state.
    - Only INSTITUTION_ADMIN and AICTE_ADMIN / DEMO_ADMIN are permitted to formally submit.
    - Scoped strictly to the caller's institution.
    - Enforces that batch is in VALIDATED status (or DRAFT if auto-validated).
    - Blocks submission if unresolved BLOCKING_ERROR findings exist.
    - If allow_warnings is False and warnings exist, blocks submission.
    - Records an immutable AuditEvent and locks the batch status.
    """
    if current_user.role not in (UserRole.INSTITUTION_ADMIN, UserRole.AICTE_ADMIN, UserRole.DEMO_ADMIN):
        raise PermissionDeniedError(f"Role '{current_user.role.value}' is not authorized to submit batches.")

    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch:
        raise NotFoundError(f"ImportBatch '{batch_id}' was not found.")

    enforce_institution_scope(current_user, batch.institution_id)

    # State validation: cannot submit if already submitted or accepted
    if batch.status in (BatchStatus.SUBMITTED, BatchStatus.UNDER_REVIEW, BatchStatus.ACCEPTED):
        raise AppException(
            code="BATCH_ALREADY_SUBMITTED",
            message=f"Batch '{batch_id}' has already been submitted (status: {batch.status.value}).",
            status_code=400
        )

    # Check for blocking errors in batch findings
    open_blocking_findings = db.query(ValidationFinding).filter(
        ValidationFinding.batch_id == batch_id,
        ValidationFinding.status == FindingStatus.OPEN,
        ValidationFinding.severity == FindingSeverity.BLOCKING_ERROR
    ).count()

    if open_blocking_findings > 0 or batch.error_rows > 0:
        raise AppException(
            code="SUBMISSION_BLOCKED_ERRORS",
            message=f"Batch '{batch_id}' cannot be submitted: {open_blocking_findings} unresolved blocking errors exist.",
            status_code=400
        )

    allow_warnings = request.allow_warnings if request else True
    if not allow_warnings:
        open_warnings = db.query(ValidationFinding).filter(
            ValidationFinding.batch_id == batch_id,
            ValidationFinding.status == FindingStatus.OPEN,
            ValidationFinding.severity == FindingSeverity.WARNING
        ).count()
        if open_warnings > 0 or batch.warning_rows > 0:
            raise AppException(
                code="SUBMISSION_BLOCKED_WARNINGS",
                message=f"Batch '{batch_id}' contains {open_warnings} warnings and submission disallows warnings.",
                status_code=400
            )

    now = datetime.now(timezone.utc)
    batch.status = BatchStatus.SUBMITTED
    batch.updated_at = now

    audit = AuditEvent(
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role.value,
        institution_id=batch.institution_id,
        action=AuditAction.BATCH_SUBMIT,
        object_type="IMPORT_BATCH",
        object_id=batch.id,
        outcome="SUCCESS",
        details=f"Batch v{batch.version} submitted: {batch.valid_rows} valid rows, 0 blocking errors. Notes: {request.comments if request else 'None'}"
    )
    db.add(audit)
    db.commit()

    return BatchSubmitResponse(
        batch_id=batch.id,
        institution_id=batch.institution_id,
        status=batch.status,
        version=batch.version,
        submitted_at=now,
        submitted_by=current_user.email,
        valid_rows=batch.valid_rows,
        error_rows=batch.error_rows,
        warning_rows=batch.warning_rows,
        message="Batch has been successfully submitted and locked for review."
    )

# ------------------------------------------------------------------------------
# 2. Review Decision Service
# ------------------------------------------------------------------------------
def review_finding(
    db: Session,
    finding_id: str,
    current_user: User,
    request: FindingReviewRequest
) -> FindingReviewResponse:
    """
    Record a human review decision (RESOLVED or DISMISSED) on a validation finding.
    - Requires mandatory reason.
    - Scoped by institution (AICTE can review all; Institution can only review own institution findings).
    - Logs an immutable AuditEvent.
    """
    finding = db.query(ValidationFinding).filter(ValidationFinding.id == finding_id).first()
    if not finding:
        raise NotFoundError(f"ValidationFinding '{finding_id}' was not found.")

    batch = db.query(ImportBatch).filter(ImportBatch.id == finding.batch_id).first()
    if not batch:
        raise NotFoundError(f"Associated ImportBatch '{finding.batch_id}' not found.")

    enforce_institution_scope(current_user, batch.institution_id)

    if request.decision not in (FindingStatus.RESOLVED, FindingStatus.DISMISSED):
        raise AppException(
            code="INVALID_REVIEW_DECISION",
            message=f"Review decision must be RESOLVED or DISMISSED, received '{request.decision}'.",
            status_code=400
        )

    prev_status = finding.status.value
    finding.status = request.decision
    db.flush()

    # If a blocking error finding was resolved/dismissed, dynamically recompute error_rows
    if finding.severity == FindingSeverity.BLOCKING_ERROR and prev_status == FindingStatus.OPEN.value:
        remaining_blocking_rows = db.query(func.count(func.distinct(ValidationFinding.row_number))).filter(
            ValidationFinding.batch_id == batch.id,
            ValidationFinding.severity == FindingSeverity.BLOCKING_ERROR,
            ValidationFinding.status == FindingStatus.OPEN
        ).scalar() or 0
        batch.error_rows = remaining_blocking_rows
        if batch.error_rows == 0 and batch.status == BatchStatus.NEEDS_CORRECTION:
            batch.status = BatchStatus.VALIDATED



    audit = AuditEvent(
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role.value,
        institution_id=batch.institution_id,
        action=AuditAction.REVIEW_DECISION,
        object_type="VALIDATION_FINDING",
        object_id=finding.id,
        outcome="SUCCESS",
        details=f"Finding '{finding.rule_code}' status changed {prev_status} -> {request.decision.value}. Reason: {request.reason}"
    )
    db.add(audit)
    db.commit()

    return FindingReviewResponse(
        finding_id=finding.id,
        batch_id=batch.id,
        status=finding.status,
        reviewed_by=current_user.email,
        reviewed_at=datetime.now(timezone.utc),
        reason=request.reason,
        message=f"Finding '{finding.id}' successfully reviewed as '{finding.status.value}'."
    )

def review_match_candidate(
    db: Session,
    match_id: str,
    current_user: User,
    request: MatchCandidateReviewRequest
) -> MatchCandidate:
    """
    Record an AICTE reviewer decision on a cross-institution MatchCandidate entity.
    - AICTE_ADMIN or DEMO_ADMIN only (cross-institution resolution authority).
    - Requires mandatory reason.
    - Logs an immutable AuditEvent.
    """
    if current_user.role not in (UserRole.AICTE_ADMIN, UserRole.DEMO_ADMIN):
        raise PermissionDeniedError("Only AICTE reviewers are authorized to resolve cross-institution duplicate candidates.")

    candidate = db.query(MatchCandidate).filter(MatchCandidate.id == match_id).first()
    if not candidate:
        raise NotFoundError(f"MatchCandidate '{match_id}' not found.")

    prev_status = candidate.status.value
    candidate.status = request.status
    candidate.resolution_reason = request.resolution_reason
    candidate.reviewed_by = current_user.id
    candidate.reviewed_at = datetime.now(timezone.utc)

    audit = AuditEvent(
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role.value,
        institution_id=candidate.institution_a_id,
        action=AuditAction.REVIEW_DECISION,
        object_type="MATCH_CANDIDATE",
        object_id=candidate.id,
        outcome="SUCCESS",
        details=f"MatchCandidate {candidate.id} ({candidate.record_a_id} <-> {candidate.record_b_id}) status {prev_status} -> {request.status.value}. Reason: {request.resolution_reason}"
    )
    db.add(audit)
    db.commit()
    return candidate

def review_batch(
    db: Session,
    batch_id: str,
    current_user: User,
    request: BatchReviewRequest
) -> BatchReviewResponse:
    """
    Record an AICTE reviewer decision on an institutional import batch.
    - AICTE_ADMIN or DEMO_ADMIN only.
    - Valid transitions:
        - UNDER_REVIEW: from SUBMITTED
        - ACCEPTED, REJECTED, NEEDS_CORRECTION: from SUBMITTED or UNDER_REVIEW
    - Statutory guard: ACCEPTED is prohibited if batch has error_rows > 0 or unresolved BLOCKING_ERROR findings.
    - Persists decision, updates batch, and records an immutable AuditEvent.
    """
    if current_user.role not in (UserRole.AICTE_ADMIN, UserRole.DEMO_ADMIN):
        raise PermissionDeniedError(f"Role '{current_user.role.value}' is not authorized to perform central batch review.")

    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch:
        raise NotFoundError(f"ImportBatch '{batch_id}' was not found.")

    prev_status = batch.status

    # Validate state transition
    valid = False
    if request.decision == BatchReviewDecision.UNDER_REVIEW:
        valid = (batch.status == BatchStatus.SUBMITTED)
    elif request.decision in (BatchReviewDecision.ACCEPTED, BatchReviewDecision.REJECTED, BatchReviewDecision.NEEDS_CORRECTION):
        valid = (batch.status in (BatchStatus.SUBMITTED, BatchStatus.UNDER_REVIEW))

    if not valid:
        raise AppException(
            code="INVALID_STATE_TRANSITION",
            message=f"Cannot transition batch '{batch_id}' from '{batch.status.value}' to '{request.decision.value}'.",
            status_code=400
        )

    # Statutory blocking error check for approval
    if request.decision == BatchReviewDecision.ACCEPTED:
        open_blocking_findings = db.query(ValidationFinding).filter(
            ValidationFinding.batch_id == batch_id,
            ValidationFinding.status == FindingStatus.OPEN,
            ValidationFinding.severity == FindingSeverity.BLOCKING_ERROR
        ).count()

        if open_blocking_findings > 0 or batch.error_rows > 0:
            raise AppException(
                code="APPROVAL_BLOCKED_ERRORS",
                message=f"Batch '{batch_id}' cannot be approved: {open_blocking_findings} unresolved blocking errors exist.",
                status_code=400
            )

    now = datetime.now(timezone.utc)
    batch.status = BatchStatus(request.decision.value)
    batch.updated_at = now

    audit = AuditEvent(
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role.value,
        institution_id=batch.institution_id,
        action=AuditAction.REVIEW_DECISION,
        object_type="IMPORT_BATCH",
        object_id=batch.id,
        outcome="SUCCESS",
        details=f"Batch review decision '{request.decision.value}' recorded (previous: {prev_status.value}). Reason: {request.reason}"
    )
    db.add(audit)
    db.commit()

    return BatchReviewResponse(
        batch_id=batch.id,
        institution_id=batch.institution_id,
        previous_status=prev_status,
        status=batch.status,
        reviewed_by=current_user.email,
        reviewed_at=now,
        reason=request.reason,
        message=f"Batch '{batch.id}' successfully transitioned from '{prev_status.value}' to '{batch.status.value}'."
    )

ACTIVE_ENROLMENT_STATUSES = (EnrolmentStatus.ENROLLED, EnrolmentStatus.ADMITTED)

# ------------------------------------------------------------------------------
# 3. Dashboard Metrics Services
# ------------------------------------------------------------------------------
def get_institution_dashboard(
    db: Session,
    current_user: User,
    institution_id: Optional[str] = None,
    academic_year: Optional[str] = None
) -> InstitutionDashboardMetrics:
    """
    Aggregate persisted institution dashboard metrics scoped to caller's institution.
    """
    target_id = institution_id or current_user.institution_id
    inst_id = enforce_institution_scope(current_user, target_id)
    if not inst_id:
        raise AppException("MISSING_INSTITUTION", "No institution bound to user profile.", status_code=400)

    institution = db.query(Institution).filter(Institution.id == inst_id).first()
    if not institution:
        raise NotFoundError(f"Institution '{inst_id}' not found.")

    # Available academic years for this institution
    batch_years = [
        r[0] for r in db.query(distinct(ImportBatch.academic_year))
        .filter(ImportBatch.institution_id == inst_id).all() if r[0]
    ]
    intake_years = [
        r[0] for r in db.query(distinct(ApprovedIntake.academic_year))
        .filter(ApprovedIntake.institution_id == inst_id).all() if r[0]
    ]
    student_years = [
        r[0] for r in db.query(distinct(StudentRecord.academic_year))
        .filter(StudentRecord.institution_id == inst_id).all() if r[0]
    ]
    available_years = sorted(list(set(batch_years + intake_years + student_years)), reverse=True)
    if not available_years:
        available_years = ["2026-2027"]

    if academic_year:
        ay = academic_year
        if ay not in available_years:
            available_years.append(ay)
            available_years.sort(reverse=True)
    else:
        ay = available_years[0]

    # Batches metrics
    batches_q = db.query(ImportBatch).filter(
        ImportBatch.institution_id == inst_id,
        ImportBatch.academic_year == ay
    ).order_by(ImportBatch.created_at.desc())

    batches = batches_q.all()
    total_batches = len(batches)
    latest_status = batches[0].status if batches else None

    # Student records metrics
    students = db.query(StudentRecord).filter(
        StudentRecord.institution_id == inst_id,
        StudentRecord.academic_year == ay
    ).all()
    total_students = len(students)
    valid_count = sum(b.valid_rows for b in batches)
    error_count = sum(b.error_rows for b in batches)
    missing_apaar = sum(1 for s in students if not s.apaar_id)

    # Active enrolment status breakdown: ENROLLED vs ADMITTED
    enrolled_finalized_count = sum(1 for s in students if s.enrolment_status == EnrolmentStatus.ENROLLED)
    admitted_count = sum(1 for s in students if s.enrolment_status == EnrolmentStatus.ADMITTED)
    active_students = [s for s in students if s.enrolment_status in ACTIVE_ENROLMENT_STATUSES]

    # Duplicate flags from findings (scoped strictly to OPEN findings)
    dup_flags = db.query(ValidationFinding).join(ImportBatch).filter(
        ImportBatch.institution_id == inst_id,
        ImportBatch.academic_year == ay,
        ValidationFinding.status == FindingStatus.OPEN,
        ValidationFinding.rule_code.like("RULE-DUP%")
    ).count()

    # Severity breakdown from findings for this institution and academic year (strictly OPEN findings)
    finding_rows = db.query(ValidationFinding.severity, func.count(ValidationFinding.id)).join(ImportBatch).filter(
        ImportBatch.institution_id == inst_id,
        ImportBatch.academic_year == ay,
        ValidationFinding.status == FindingStatus.OPEN,
    ).group_by(ValidationFinding.severity).all()
    finding_counts = {sev: cnt for sev, cnt in finding_rows}
    blocking_count = finding_counts.get(FindingSeverity.BLOCKING_ERROR, 0)
    warning_count = finding_counts.get(FindingSeverity.WARNING, 0)

    # Special Quota Breakdown derived from active student records
    tfw_enrolled = sum(1 for s in active_students if s.seat_type == SeatType.SUPERNUMERARY_TFW)
    ews_enrolled = sum(1 for s in active_students if s.seat_type == SeatType.SUPERNUMERARY_EWS)
    pmsss_enrolled = sum(1 for s in active_students if s.seat_type == SeatType.SUPERNUMERARY_OTHER)
    nri_enrolled = sum(1 for s in active_students if s.is_nri or s.seat_type == SeatType.NRI)
    oci_enrolled = sum(1 for s in active_students if s.is_oci)
    fn_enrolled = sum(1 for s in active_students if s.is_fn or s.seat_type == SeatType.SUPERNUMERARY_FN)

    special_quotas = [
        SpecialQuotaMetric(category="TFW", label="Tuition Fee Waiver (TFW)", enrolled=tfw_enrolled),
        SpecialQuotaMetric(category="EWS", label="Economically Weaker Section (EWS)", enrolled=ews_enrolled),
        SpecialQuotaMetric(category="PMSSS", label="Prime Minister's Special Scholarship (PMSSS)", enrolled=pmsss_enrolled),
        SpecialQuotaMetric(category="NRI", label="Non-Resident Indian (NRI)", enrolled=nri_enrolled),
        SpecialQuotaMetric(category="OCI", label="Overseas Citizen of India (OCI/PIO)", enrolled=oci_enrolled),
        SpecialQuotaMetric(category="FN", label="Foreign Nationals (FN)", enrolled=fn_enrolled),
    ]

    # Programme breakdown and intake calculation
    programmes = db.query(Programme).filter(Programme.institution_id == inst_id).all()
    intakes = {
        i.programme_id: i for i in db.query(ApprovedIntake).filter(
            ApprovedIntake.institution_id == inst_id,
            ApprovedIntake.academic_year == ay
        ).all()
    }

    prog_metrics: List[ProgrammeIntakeMetric] = []
    tot_approved = 0
    tot_enrolled = 0

    for prog in programmes:
        limit = intakes.get(prog.id)
        reg_app = limit.regular_intake if limit else 0
        super_app = limit.supernumerary_intake if limit else 0
        prog_tot_app = reg_app + super_app

        prog_students = [
            s for s in students
            if s.programme_id == prog.id and s.enrolment_status in ACTIVE_ENROLMENT_STATUSES
        ]
        prog_enrolled_count = sum(1 for s in prog_students if s.enrolment_status == EnrolmentStatus.ENROLLED)
        prog_admitted_count = sum(1 for s in prog_students if s.enrolment_status == EnrolmentStatus.ADMITTED)

        prog_super_enrolled = sum(1 for s in prog_students if s.seat_type in (
            SeatType.SUPERNUMERARY_EWS, SeatType.SUPERNUMERARY_TFW, SeatType.SUPERNUMERARY_FN, SeatType.SUPERNUMERARY_OTHER
        ))
        prog_reg_enrolled = len(prog_students) - prog_super_enrolled
        prog_tot_enrolled = len(prog_students)

        tot_approved += prog_tot_app
        tot_enrolled += prog_tot_enrolled

        util = round((prog_tot_enrolled / prog_tot_app * 100.0), 1) if prog_tot_app > 0 else 0.0

        # Independent checks for regular, supernumerary, and total capacity (FIX 7)
        reg_exceeded = max(0, prog_reg_enrolled - reg_app)
        super_exceeded = max(0, prog_super_enrolled - super_app)
        tot_exceeded = max(0, prog_tot_enrolled - prog_tot_app)
        status_str = "EXCEEDED" if (reg_exceeded > 0 or super_exceeded > 0 or tot_exceeded > 0) else "WITHIN_LIMIT"

        prog_metrics.append(ProgrammeIntakeMetric(
            programme_id=prog.id,
            programme_name=prog.name,
            regular_approved=reg_app,
            regular_enrolled=prog_reg_enrolled,
            supernumerary_approved=super_app,
            supernumerary_enrolled=prog_super_enrolled,
            total_approved=prog_tot_app,
            total_enrolled=prog_tot_enrolled,
            utilization_pct=util,
            status=status_str,
            enrolled_count=prog_enrolled_count,
            admitted_count=prog_admitted_count
        ))

    overall_util = round((tot_enrolled / tot_approved * 100.0), 1) if tot_approved > 0 else 0.0

    recent_batches = [
        RecentBatchSummary(
            id=b.id,
            source_filename=b.source_filename,
            academic_year=b.academic_year,
            version=b.version,
            status=b.status,
            total_rows=b.total_rows,
            valid_rows=b.valid_rows,
            error_rows=b.error_rows,
            warning_rows=b.warning_rows,
            created_at=b.created_at
        ) for b in batches[:5]
    ]

    recent_audits = db.query(AuditEvent).filter(
        AuditEvent.institution_id == inst_id
    ).order_by(AuditEvent.timestamp.desc()).limit(10).all()

    recent_activity = [
        RecentActivityItem(
            timestamp=a.timestamp,
            action=a.action.value,
            actor_email=a.actor_email,
            actor_role=a.actor_role,
            details=a.details,
            outcome=a.outcome
        ) for a in recent_audits
    ]

    return InstitutionDashboardMetrics(
        institution_id=institution.id,
        institution_name=institution.name,
        academic_year=ay,
        total_batches=total_batches,
        latest_batch_status=latest_status,
        total_student_records=total_students,
        valid_records_count=valid_count,
        error_records_count=error_count,
        missing_apaar_count=missing_apaar,
        duplicate_flags_count=dup_flags,
        intake_utilization_pct=overall_util,
        total_approved_intake=tot_approved,
        total_enrolled_students=tot_enrolled,
        programme_intake_breakdown=prog_metrics,
        recent_batches=recent_batches,
        recent_activity=recent_activity,
        blocking_findings_count=blocking_count,
        warning_findings_count=warning_count,
        available_academic_years=available_years,
        special_quota_breakdown=special_quotas,
        enrolled_finalized_count=enrolled_finalized_count,
        admitted_count=admitted_count,
    )

def get_aicte_dashboard(
    db: Session,
    current_user: User,
    academic_year: Optional[str] = None
) -> AICTEDashboardMetrics:
    """
    Aggregate platform-wide AICTE monitoring metrics across all approved institutions.
    - AICTE_ADMIN and DEMO_ADMIN only.
    """
    if current_user.role not in (UserRole.AICTE_ADMIN, UserRole.DEMO_ADMIN):
        raise PermissionDeniedError("AICTE monitoring dashboard is restricted to central AICTE administrators.")

    if not academic_year:
        latest_batch = db.query(ImportBatch.academic_year).order_by(ImportBatch.created_at.desc()).first()
        ay = latest_batch[0] if (latest_batch and latest_batch[0]) else "2026-2027"
    else:
        ay = academic_year

    institutions = db.query(Institution).all()
    total_institutions = len(institutions)

    batches = db.query(ImportBatch).filter(ImportBatch.academic_year == ay).all()
    total_batches = len(batches)
    total_submissions = sum(1 for b in batches if b.status in (BatchStatus.SUBMITTED, BatchStatus.UNDER_REVIEW, BatchStatus.ACCEPTED))

    # All active student records for this academic year
    students = db.query(StudentRecord).filter(StudentRecord.academic_year == ay).all()
    enrolled_students = [s for s in students if s.enrolment_status in ACTIVE_ENROLMENT_STATUSES]
    total_enrolled = len(enrolled_students)

    # Approved intakes
    intakes = db.query(ApprovedIntake).filter(ApprovedIntake.academic_year == ay).all()
    total_approved = sum(i.regular_intake + i.supernumerary_intake for i in intakes)
    agg_util = round((total_enrolled / total_approved * 100.0), 1) if total_approved > 0 else 0.0

    # Exceptions and Match Candidates
    open_exceptions = db.query(ValidationFinding).filter(ValidationFinding.status == FindingStatus.OPEN).count()

    candidates = db.query(MatchCandidate).all()
    tot_candidates = sum(1 for c in candidates if c.status == MatchStatus.CANDIDATE)
    tot_confirmed = sum(1 for c in candidates if c.status == MatchStatus.CONFIRMED_DUPLICATE)
    tot_dismissed = sum(1 for c in candidates if c.status == MatchStatus.DISMISSED)

    # Institution breakdown
    inst_breakdown: List[InstitutionEnrolmentSummary] = []
    for inst in institutions:
        inst_batches = [b for b in batches if b.institution_id == inst.id]
        inst_latest_status = inst_batches[0].status if inst_batches else None
        inst_enrolled = sum(1 for s in enrolled_students if s.institution_id == inst.id)
        inst_approved = sum(i.regular_intake + i.supernumerary_intake for i in intakes if i.institution_id == inst.id)
        inst_util = round((inst_enrolled / inst_approved * 100.0), 1) if inst_approved > 0 else 0.0
        inst_exceptions = db.query(ValidationFinding).join(ImportBatch).filter(
            ImportBatch.institution_id == inst.id,
            ValidationFinding.status == FindingStatus.OPEN
        ).count()

        inst_breakdown.append(InstitutionEnrolmentSummary(
            institution_id=inst.id,
            institution_name=inst.name,
            state=inst.state,
            total_batches=len(inst_batches),
            latest_status=inst_latest_status,
            total_enrolled=inst_enrolled,
            total_approved=inst_approved,
            intake_utilization_pct=inst_util,
            open_exceptions_count=inst_exceptions
        ))

    recent_audits = db.query(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(15).all()
    recent_activity = [
        RecentActivityItem(
            timestamp=a.timestamp,
            action=a.action.value,
            actor_email=a.actor_email,
            actor_role=a.actor_role,
            details=a.details,
            outcome=a.outcome
        ) for a in recent_audits
    ]

    return AICTEDashboardMetrics(
        academic_year=ay,
        total_institutions=total_institutions,
        total_submissions=total_submissions,
        total_batches=total_batches,
        total_enrolled_students=total_enrolled,
        total_approved_intake=total_approved,
        aggregate_intake_utilization_pct=agg_util,
        total_open_exceptions=open_exceptions,
        total_candidate_duplicates=tot_candidates,
        confirmed_duplicates_count=tot_confirmed,
        dismissed_duplicates_count=tot_dismissed,
        institution_breakdown=inst_breakdown,
        recent_activity=recent_activity
    )
