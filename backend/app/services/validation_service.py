import re
import uuid
from typing import Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from backend.app.core.config import settings
from backend.app.core.errors import AppException, NotFoundError, PermissionDeniedError
from backend.app.core.permissions import enforce_institution_scope
from backend.app.models.audit import AuditEvent
from backend.app.models.batch import ImportBatch
from backend.app.models.enums import (
    AuditAction,
    BatchStatus,
    EnrolmentStatus,
    FindingSeverity,
    FindingStatus,
    MatchStatus,
    SeatType,
    UserRole,
)
from backend.app.models.institution import ApprovedIntake, Institution, Programme
from backend.app.models.match import MatchCandidate
from backend.app.models.student import StudentRecord
from backend.app.models.user import User
from backend.app.models.validation import ValidationFinding
from backend.app.schemas.validation import (
    BatchValidationResponse,
    IntakeReconciliationSummary,
    ValidationSummary,
)

# ------------------------------------------------------------------------------
# Verhoeff Algorithm Tables for Synthetic Checksum Verification
# ------------------------------------------------------------------------------
VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

VERHOEFF_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

def validate_verhoeff_checksum(num_str: str) -> bool:
    """
    Validate string of digits against standard Verhoeff algorithm.
    Returns True if checksum passes.
    """
    if not num_str.isdigit():
        return False
    c = 0
    reversed_digits = [int(x) for x in reversed(num_str)]
    for i, digit in enumerate(reversed_digits):
        c = VERHOEFF_D[c][VERHOEFF_P[i % 8][digit]]
    return c == 0

def check_apaar_syntax(apaar_id: Optional[str]) -> Tuple[bool, Optional[str], FindingSeverity]:
    """
    Validate APAAR ID presence and syntax.
    Returns: (is_valid, message, severity)
    NOTE: This is a configurable syntactic format check only; it does not claim
    official UIDAI or Ministry of Education APAAR verification.
    """
    if not apaar_id:
        if settings.APAAR_MANDATORY:
            return False, "APAAR ID is missing for student record (mandatory under strict institution policy).", FindingSeverity.BLOCKING_ERROR
        return False, "APAAR ID is unassigned for student record. Student must register on Academic Bank of Credits.", FindingSeverity.WARNING

    cleaned = str(apaar_id).strip()
    if len(cleaned) != settings.APAAR_ID_LENGTH or not cleaned.isdigit():
        return False, f"APAAR ID '{cleaned}' does not match standard {settings.APAAR_ID_LENGTH}-digit numeric format.", FindingSeverity.BLOCKING_ERROR

    if settings.ENFORCE_VERHOEFF_CHECKSUM:
        if not validate_verhoeff_checksum(cleaned):
            return False, f"APAAR ID '{cleaned}' failed checksum validation. Please verify the 12-digit number.", FindingSeverity.BLOCKING_ERROR

    return True, None, FindingSeverity.INFO

def is_match_candidate_pair_conflict(exc: IntegrityError) -> bool:
    """
    Determine if an IntegrityError was caused specifically by a collision on the
    match_candidates unique pair index (uq_match_candidates_pair).
    Inspects exception strings, dialect-specific orig attributes, and table references
    while avoiding misclassification of foreign key or other column constraints.
    """
    orig_str = str(getattr(exc, "orig", exc)).lower()
    full_str = str(exc).lower()

    # Direct match on the unique index name
    if "uq_match_candidates_pair" in full_str or "uq_match_candidates_pair" in orig_str:
        return True

    # SQLite specific index conflict pattern
    if "unique constraint failed" in orig_str or "unique constraint failed" in full_str:
        if "match_candidates" in orig_str or "match_candidates" in full_str:
            return True

    return False

# ------------------------------------------------------------------------------
# Core Validation & Reconciliation Engine
# ------------------------------------------------------------------------------
def execute_batch_validation(
    db: Session,
    batch_id: str,
    current_user: User
) -> BatchValidationResponse:
    """
    Run the deterministic Core Validation & Intake Reconciliation Engine on an ImportBatch.
    1. Enforces institution data isolation.
    2. Clears previous automated findings for idempotency.
    3. Evaluates Rule 1: Required Student Name & Identifiers.
    4. Evaluates Rule 2: APAAR ID Presence & Syntactic Format.
    5. Evaluates Rule 3: Academic Programme existence and validity.
    6. Evaluates Rule 4: Quota & International Category consistency (NRI/OCI/FN vs SeatType).
    7. Evaluates Rule 5: Intra-institution duplicates within batch and historical scope.
    8. Evaluates Rule 6: Cross-institution candidate duplicate match detection.
    9. Evaluates Rule 7: Approved Intake limits & Supernumerary seat exceedance.
    10. Updates ImportBatch metrics, status (VALIDATED / NEEDS_CORRECTION), and records AuditEvent.
    """
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch:
        raise NotFoundError(f"ImportBatch '{batch_id}' was not found.")

    # Enforce Server-Side Scoping
    enforce_institution_scope(current_user, batch.institution_id)

    # Preload Batch Records
    records = db.query(StudentRecord).filter(StudentRecord.batch_id == batch_id).all()
    if not records:
        raise AppException("EMPTY_BATCH", "Batch contains no persisted student records to validate.", status_code=400)

    # 1. Clear previous validation-stage findings for this batch to ensure idempotent re-runs,
    # while preserving import-stage findings for rejected rows that have no persisted student record.
    db.query(ValidationFinding).filter(
        ValidationFinding.batch_id == batch_id,
        ValidationFinding.status == FindingStatus.OPEN,
        (ValidationFinding.record_id.isnot(None) | (ValidationFinding.rule_code == "RULE-INTAKE-001"))
    ).delete(synchronize_session=False)

    findings: List[ValidationFinding] = []
    # Count any existing preserved import-stage blocking errors (e.g. unpersisted rejected rows)
    existing_import_findings = db.query(ValidationFinding).filter(
        ValidationFinding.batch_id == batch_id,
        ValidationFinding.status == FindingStatus.OPEN
    ).all()
    blocking_error_count = len([f for f in existing_import_findings if f.severity == FindingSeverity.BLOCKING_ERROR])
    warning_count = len([f for f in existing_import_findings if f.severity == FindingSeverity.WARNING])
    info_count = 0

    # Preload approved programmes and intakes for this institution
    inst_id = batch.institution_id
    acad_year = batch.academic_year
    programmes = {p.id: p for p in db.query(Programme).filter(Programme.institution_id == inst_id).all()}
    intakes = {
        i.programme_id: i for i in db.query(ApprovedIntake).filter(
            ApprovedIntake.institution_id == inst_id,
            ApprovedIntake.academic_year == acad_year
        ).all()
    }

    # Tracking sets for duplicate evaluation
    seen_inst_student_ids: Dict[str, StudentRecord] = {}
    seen_apaars: Dict[str, StudentRecord] = {}

    # Preload cross-batch student records within same institution and academic year
    other_institution_records = db.query(StudentRecord).filter(
        StudentRecord.institution_id == inst_id,
        StudentRecord.academic_year == acad_year,
        StudentRecord.batch_id != batch_id
    ).all()
    hist_inst_student_ids = {r.institution_student_id: r for r in other_institution_records if r.institution_student_id}
    hist_apaars = {r.apaar_id: r for r in other_institution_records if r.apaar_id}

    # Collect distinct non-null APAAR IDs present in this batch
    batch_apaars = list({r.apaar_id for r in records if r.apaar_id})

    # Preload cross-institution records for central duplicate detection (AICTE scope)
    # Filtered strictly to the APAAR IDs in the current batch to avoid unbounded table scans
    cross_inst_apaars = {}
    if batch_apaars:
        cross_inst_apaars = {
            r.apaar_id: r for r in db.query(StudentRecord).filter(
                StudentRecord.institution_id != inst_id,
                StudentRecord.academic_year == acad_year,
                StudentRecord.apaar_id.in_(batch_apaars)
            ).all()
        }

    # Program enrolled counts accumulator for cumulative intake reconciliation
    # We initialize with eligible enrolled students from prior batches of the same institution, programme and academic year
    prog_counts: Dict[str, Dict[str, int]] = {}
    for hist_rec in other_institution_records:
        if hist_rec.programme_id in programmes and hist_rec.enrolment_status in (EnrolmentStatus.ENROLLED, EnrolmentStatus.ADMITTED):
            p_counts = prog_counts.setdefault(hist_rec.programme_id, {"REGULAR": 0, "SUPERNUMERARY": 0, "TOTAL": 0})
            p_counts["TOTAL"] += 1
            if hist_rec.seat_type in (
                SeatType.SUPERNUMERARY_EWS,
                SeatType.SUPERNUMERARY_TFW,
                SeatType.SUPERNUMERARY_FN,
                SeatType.SUPERNUMERARY_OTHER
            ):
                p_counts["SUPERNUMERARY"] += 1
            else:
                p_counts["REGULAR"] += 1

    # Set of distinct record IDs in this batch that have at least one blocking error
    invalid_record_ids: Set[str] = set()

    # 2. Iterate Student Records for Field and Entity Checks
    for idx, rec in enumerate(records, start=1):
        effective_row_num = rec.source_row_number if rec.source_row_number is not None else idx
        rec_has_blocking_error = False

        # --- Rule 1: Student Name presence & formatting ---
        if not rec.student_name or len(rec.student_name.strip()) < 2:
            rec_has_blocking_error = True
            invalid_record_ids.add(rec.id)
            blocking_error_count += 1
            findings.append(ValidationFinding(
                batch_id=batch_id,
                record_id=rec.id,
                row_number=effective_row_num,
                field_name="student_name",
                rule_code="RULE-REQ-001",
                severity=FindingSeverity.BLOCKING_ERROR,
                message="Student name is mandatory and must contain at least 2 characters.",
                actual_value=rec.student_name,
                suggested_action="Provide the full legal name of the candidate."
            ))

        # --- Rule 2: APAAR ID Syntactic Format & Presence ---
        apaar_valid, apaar_msg, apaar_sev = check_apaar_syntax(rec.apaar_id)
        if not apaar_valid:
            if apaar_sev == FindingSeverity.BLOCKING_ERROR:
                rec_has_blocking_error = True
                invalid_record_ids.add(rec.id)
                blocking_error_count += 1
            elif apaar_sev == FindingSeverity.WARNING:
                warning_count += 1
            findings.append(ValidationFinding(
                batch_id=batch_id,
                record_id=rec.id,
                row_number=effective_row_num,
                field_name="apaar_id",
                rule_code="RULE-APAAR-001" if not rec.apaar_id else "RULE-APAAR-002",
                severity=apaar_sev,
                message=apaar_msg,
                actual_value=rec.apaar_id,
                suggested_action="Verify student 12-digit APAAR/ABC ID or initiate APAAR creation."
            ))

        # --- Rule 3: Programme Existence ---
        if rec.programme_id not in programmes:
            rec_has_blocking_error = True
            invalid_record_ids.add(rec.id)
            blocking_error_count += 1
            findings.append(ValidationFinding(
                batch_id=batch_id,
                record_id=rec.id,
                row_number=effective_row_num,
                field_name="programme_id",
                rule_code="RULE-REQ-003",
                severity=FindingSeverity.BLOCKING_ERROR,
                message=f"Programme '{rec.programme_id}' is not an approved programme for this institution.",
                actual_value=rec.programme_id,
                suggested_action="Map student to an active, approved academic programme."
            ))

        # --- Rule 4: Quota & Category Consistency ---
        # e.g., NRI flag is True, but seat_type is not NRI or SUPERNUMERARY
        if rec.is_nri and rec.seat_type not in (SeatType.NRI, SeatType.SUPERNUMERARY_FN, SeatType.SUPERNUMERARY_OTHER, SeatType.MANAGEMENT):
            warning_count += 1
            findings.append(ValidationFinding(
                batch_id=batch_id,
                record_id=rec.id,
                row_number=effective_row_num,
                field_name="seat_type",
                rule_code="RULE-CAT-001",
                severity=FindingSeverity.WARNING,
                message=f"Student marked as NRI candidate, but seat quota is set to '{rec.seat_type.value}'.",
                actual_value=rec.seat_type.value,
                suggested_action="Verify whether student is admitted against NRI or General quota."
            ))

        if (rec.is_fn or rec.is_oci) and rec.seat_type not in (SeatType.SUPERNUMERARY_FN, SeatType.SUPERNUMERARY_OTHER, SeatType.MANAGEMENT, SeatType.NRI):
            warning_count += 1
            findings.append(ValidationFinding(
                batch_id=batch_id,
                record_id=rec.id,
                row_number=effective_row_num,
                field_name="seat_type",
                rule_code="RULE-CAT-002",
                severity=FindingSeverity.WARNING,
                message="Foreign National / OCI student admitted against regular domestic seat quota.",
                actual_value=rec.seat_type.value,
                suggested_action="Review AICTE supernumerary guidelines for Foreign Nationals (Chapter II)."
            ))

        # --- Rule 5: Intra-Institution Exact Duplicates ---
        # Duplicate roll within current batch
        if rec.institution_student_id in seen_inst_student_ids:
            rec_has_blocking_error = True
            invalid_record_ids.add(rec.id)
            blocking_error_count += 1
            first_seen = seen_inst_student_ids[rec.institution_student_id]
            findings.append(ValidationFinding(
                batch_id=batch_id,
                record_id=rec.id,
                row_number=effective_row_num,
                field_name="institution_student_id",
                rule_code="RULE-DUP-001",
                severity=FindingSeverity.BLOCKING_ERROR,
                message=f"Duplicate Student Roll Number '{rec.institution_student_id}' conflicts with record '{first_seen.id}'.",
                actual_value=rec.institution_student_id,
                suggested_action="Remove duplicate record from batch."
            ))
        else:
            seen_inst_student_ids[rec.institution_student_id] = rec

        # Duplicate roll across previous batches
        if rec.institution_student_id in hist_inst_student_ids:
            rec_has_blocking_error = True
            invalid_record_ids.add(rec.id)
            blocking_error_count += 1
            prev = hist_inst_student_ids[rec.institution_student_id]
            findings.append(ValidationFinding(
                batch_id=batch_id,
                record_id=rec.id,
                row_number=effective_row_num,
                field_name="institution_student_id",
                rule_code="RULE-DUP-002",
                severity=FindingSeverity.BLOCKING_ERROR,
                message=f"Student Roll Number '{rec.institution_student_id}' already enrolled in earlier batch '{prev.batch_id}'.",
                actual_value=rec.institution_student_id,
                suggested_action="Check existing student record before re-admitting."
            ))

        # Duplicate APAAR ID within batch
        if rec.apaar_id:
            if rec.apaar_id in seen_apaars:
                rec_has_blocking_error = True
                invalid_record_ids.add(rec.id)
                blocking_error_count += 1
                prior = seen_apaars[rec.apaar_id]
                findings.append(ValidationFinding(
                    batch_id=batch_id,
                    record_id=rec.id,
                    row_number=effective_row_num,
                    field_name="apaar_id",
                    rule_code="RULE-DUP-003",
                    severity=FindingSeverity.BLOCKING_ERROR,
                    message=f"APAAR ID '{rec.apaar_id}' mapped to multiple students in this batch (conflicts with '{prior.student_name}').",
                    actual_value=rec.apaar_id,
                    suggested_action="APAAR ID must uniquely identify a single student."
                ))
            else:
                seen_apaars[rec.apaar_id] = rec

                # Duplicate APAAR ID across earlier batches of same institution
                # Disentangled: only evaluated for distinct batch records, not redundant in-batch collisions
                if rec.apaar_id in hist_apaars:
                    warning_count += 1
                    prev_stu = hist_apaars[rec.apaar_id]
                    findings.append(ValidationFinding(
                        batch_id=batch_id,
                        record_id=rec.id,
                        row_number=effective_row_num,
                        field_name="apaar_id",
                        rule_code="RULE-DUP-004",
                        severity=FindingSeverity.WARNING,
                        message=f"APAAR ID '{rec.apaar_id}' was previously ingested in batch '{prev_stu.batch_id}' ({prev_stu.academic_year}).",
                        actual_value=rec.apaar_id,
                        suggested_action="Verify if student is enrolling in a second degree or repeating year."
                    ))

            # --- Rule 6: Cross-Institution Duplicate Candidate Detection ---
            if rec.apaar_id in cross_inst_apaars:
                cross_match = cross_inst_apaars[rec.apaar_id]
                warning_count += 1
                findings.append(ValidationFinding(
                    batch_id=batch_id,
                    record_id=rec.id,
                    row_number=effective_row_num,
                    field_name="apaar_id",
                    rule_code="RULE-DUP-005",
                    severity=FindingSeverity.WARNING,
                    message=f"Cross-institution dual enrolment alert: APAAR ID '{rec.apaar_id}' is also registered at '{cross_match.institution_id}'.",
                    actual_value=rec.apaar_id,
                    suggested_action="Requires AICTE Reviewer inspection under Exception Queue."
                ))

                # Stage or update MatchCandidate entity for AICTE exception queue symmetrically
                rec_a_id, rec_b_id = (rec.id, cross_match.id) if rec.id < cross_match.id else (cross_match.id, rec.id)
                inst_a_id, inst_b_id = (inst_id, cross_match.institution_id) if rec.id < cross_match.id else (cross_match.institution_id, inst_id)

                candidate = db.query(MatchCandidate).filter(
                    ((MatchCandidate.record_a_id == rec_a_id) & (MatchCandidate.record_b_id == rec_b_id)) |
                    ((MatchCandidate.record_a_id == rec_b_id) & (MatchCandidate.record_b_id == rec_a_id))
                ).first()
                if not candidate:
                    candidate = MatchCandidate(
                        id=f"mat-{uuid.uuid4().hex[:12]}",
                        record_a_id=rec_a_id,
                        record_b_id=rec_b_id,
                        institution_a_id=inst_a_id,
                        institution_b_id=inst_b_id,
                        matching_signal="EXACT_APAAR_CROSS_INSTITUTION",
                        confidence=1.0,
                        status=MatchStatus.CANDIDATE
                    )
                    db.add(candidate)

        # Accumulate counts for intake reconciliation if programme is valid and student is active
        if rec.programme_id in programmes and rec.enrolment_status in (EnrolmentStatus.ENROLLED, EnrolmentStatus.ADMITTED):
            p_counts = prog_counts.setdefault(rec.programme_id, {"REGULAR": 0, "SUPERNUMERARY": 0, "TOTAL": 0})
            p_counts["TOTAL"] += 1
            if rec.seat_type in (
                SeatType.SUPERNUMERARY_EWS,
                SeatType.SUPERNUMERARY_TFW,
                SeatType.SUPERNUMERARY_FN,
                SeatType.SUPERNUMERARY_OTHER
            ):
                p_counts["SUPERNUMERARY"] += 1
            else:
                p_counts["REGULAR"] += 1

    # --- Rule 7: Intake Reconciliation (Approved vs Actual Enrolment) ---
    intake_reconciliation: List[IntakeReconciliationSummary] = []
    intake_exceeded_total = 0

    for prog_id, prog in programmes.items():
        counts = prog_counts.get(prog_id, {"REGULAR": 0, "SUPERNUMERARY": 0, "TOTAL": 0})
        intake_limit = intakes.get(prog_id)

        reg_approved = intake_limit.regular_intake if intake_limit else 0
        super_approved = intake_limit.supernumerary_intake if intake_limit else 0
        tot_approved = reg_approved + super_approved

        reg_enrolled = counts["REGULAR"]
        super_enrolled = counts["SUPERNUMERARY"]
        tot_enrolled = counts["TOTAL"]

        reg_exceeded = max(0, reg_enrolled - reg_approved)
        super_exceeded = max(0, super_enrolled - super_approved)
        tot_exceeded = max(0, tot_enrolled - tot_approved)

        status_str = "EXCEEDED" if (reg_exceeded > 0 or super_exceeded > 0 or tot_exceeded > 0) else "WITHIN_LIMIT"
        if status_str == "EXCEEDED":
            intake_exceeded_total += tot_exceeded

            # Only emit an intake exceedance finding on this batch if this batch actually contains records for this programme
            batch_has_prog_records = any(r.programme_id == prog_id for r in records)
            if batch_has_prog_records:
                blocking_error_count += 1
                findings.append(ValidationFinding(
                    batch_id=batch_id,
                    record_id=None,
                    row_number=None,
                    field_name="intake",
                    rule_code="RULE-INTAKE-001",
                    severity=FindingSeverity.BLOCKING_ERROR,
                    message=(
                        f"Programme '{prog.name}' ({prog_id}) enrolment ({tot_enrolled}) exceeds approved AICTE intake ({tot_approved}). "
                        f"Regular: {reg_enrolled}/{reg_approved}; Supernumerary: {super_enrolled}/{super_approved}."
                    ),
                    expected_value=f"<= {tot_approved}",
                    actual_value=str(tot_enrolled),
                    suggested_action="Adjust admitted students within AICTE approved intake capacity or seek extension."
                ))

        intake_reconciliation.append(IntakeReconciliationSummary(
            programme_id=prog_id,
            programme_name=prog.name,
            academic_year=acad_year,
            regular_approved=reg_approved,
            regular_enrolled=reg_enrolled,
            regular_exceeded=reg_exceeded,
            supernumerary_approved=super_approved,
            supernumerary_enrolled=super_enrolled,
            supernumerary_exceeded=super_exceeded,
            total_approved=tot_approved,
            total_enrolled=tot_enrolled,
            total_exceeded=tot_exceeded,
            status=status_str
        ))

    # 3. Persist Findings & Update Batch State
    if findings:
        db.add_all(findings)

    # Distinct records in this batch that have no blocking errors are valid
    valid_records_count = len(records) - len(invalid_record_ids)
    batch.error_rows = len(invalid_record_ids)
    batch.warning_rows = warning_count
    batch.valid_rows = valid_records_count
    batch.status = BatchStatus.NEEDS_CORRECTION if (blocking_error_count > 0 or len(invalid_record_ids) > 0) else BatchStatus.VALIDATED

    # 4. Audit Log & Atomic Persistence
    audit = AuditEvent(
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role.value,
        institution_id=inst_id,
        action=AuditAction.BATCH_VALIDATE,
        object_type="IMPORT_BATCH",
        object_id=batch.id,
        outcome="SUCCESS",
        details=(
            f"Batch {batch_id} validated: {len(records)} records, {blocking_error_count} blocking errors, "
            f"{warning_count} warnings, status -> {batch.status.value}."
        )
    )
    db.add(audit)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # If conflict occurred on match candidate pair due to concurrent validation, retry without re-inserting match candidates.
        # Why reusing computed findings is safe:
        # 1. Validation findings (RULE-REQ, RULE-APAAR, RULE-DUP, RULE-INTAKE) are deterministic pure functions
        #    of this batch's immutable student records and current approved intake configuration.
        # 2. A collision on uq_match_candidates_pair means another concurrent validation run already created the exact
        #    same match candidate pair in the database.
        # 3. Therefore, re-running validation would compute identical findings. We safely re-apply the computed
        #    findings, update batch status/metrics, and commit without recreating the conflicting candidate.
        if is_match_candidate_pair_conflict(exc):
            batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
            if batch:
                batch.error_rows = len(invalid_record_ids)
                batch.warning_rows = warning_count
                batch.valid_rows = valid_records_count
                batch.status = BatchStatus.NEEDS_CORRECTION if (blocking_error_count > 0 or len(invalid_record_ids) > 0) else BatchStatus.VALIDATED
                if findings:
                    db.add_all(findings)
                db.add(audit)
                db.commit()
        else:
            # Re-raise any unrelated integrity error (e.g., FK violations, NULL constraints)
            raise

    val_summary = ValidationSummary(
        total_records=len(records),
        valid_records=valid_records_count,
        error_count=blocking_error_count,
        warning_count=warning_count,
        info_count=info_count,
        intake_exceeded_count=intake_exceeded_total,
        duplicate_candidate_count=len([f for f in findings if "RULE-DUP" in f.rule_code])
    )

    return BatchValidationResponse(
        batch_id=batch_id,
        institution_id=inst_id,
        status=batch.status,
        validation_summary=val_summary,
        intake_reconciliation=intake_reconciliation,
        findings_count=len(findings),
        message=f"Validation completed. Batch status set to {batch.status.value}."
    )
