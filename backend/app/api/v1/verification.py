"""
Verification API Router.
Handles privacy-preserving, purpose-restricted single-record verification lookup.
Uses replaceable APAAR adapter provider and logs immutable audit records.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.adapters import get_apaar_adapter, VerificationResult
from backend.app.core.errors import NotFoundError
from backend.app.core.permissions import get_current_user, enforce_institution_scope
from backend.app.db.session import get_db
from backend.app.models.audit import AuditEvent
from backend.app.models.enums import AuditAction, UserRole
from backend.app.models.student import StudentRecord
from backend.app.models.user import User
from backend.app.models.verification import VerificationAttempt

router = APIRouter(prefix="/verification", tags=["Verification"])

def _resolve_student_record(
    db: Session,
    student_ref: str,
    current_user: User
) -> StudentRecord:
    """
    Safely resolves a StudentRecord for the authenticated caller.
    - If caller is privileged (AICTE_ADMIN, DEMO_ADMIN, EXTERNAL_VERIFIER), searches globally.
    - If caller is institution-bound:
      1. If queried by internal student primary key (id), checks global record and enforces
         institution scope (returning 403 if IDOR attempt across institutions).
      2. If queried by domain identifier (apaar_id or institution_student_id), filters strictly
         by current_user.institution_id so cross-institution duplicates resolve safely to the
         caller's own record without collision or information leakage.
    """
    is_privileged = current_user.role in (
        UserRole.AICTE_ADMIN,
        UserRole.DEMO_ADMIN,
        UserRole.EXTERNAL_VERIFIER
    )

    if is_privileged:
        record = db.query(StudentRecord).filter(
            (StudentRecord.id == student_ref) |
            (StudentRecord.institution_student_id == student_ref) |
            (StudentRecord.apaar_id == student_ref)
        ).order_by(StudentRecord.id.asc()).first()
    else:
        # Check institution caller bound institution
        inst_id = current_user.institution_id
        if not inst_id:
            raise NotFoundError(f"Student record '{student_ref}' not found.")

        # First, check if student_ref is a record in caller's institution (by id, institution_student_id, or apaar_id)
        record = db.query(StudentRecord).filter(
            StudentRecord.institution_id == inst_id,
            (
                (StudentRecord.id == student_ref) |
                (StudentRecord.institution_student_id == student_ref) |
                (StudentRecord.apaar_id == student_ref)
            )
        ).order_by(StudentRecord.id.asc()).first()

        # If not found in caller's institution, check if student_ref is a direct primary key (id)
        # of another institution's record. If so, enforce institution scope to return 403.
        # Note: We do NOT do this for apaar_id/institution_student_id to prevent leaking identifier existence.
        if not record:
            cross_record = db.query(StudentRecord).filter(StudentRecord.id == student_ref).first()
            if cross_record:
                enforce_institution_scope(current_user, cross_record.institution_id)

    if not record:
        raise NotFoundError(f"Student record '{student_ref}' not found.")

    if not is_privileged:
        enforce_institution_scope(current_user, record.institution_id)

    return record


@router.get("/{student_ref}", response_model=VerificationResult, summary="Privacy-restricted single-record APAAR verification lookup")
def verify_student_record(
    student_ref: str,
    simulate_outage: bool = Query(False, description="Simulate provider outage for testing graceful degradation"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Perform a purpose-restricted, privacy-preserving verification check for a student.
    - Can look up by student_id, institution_student_id, or apaar_id.
    - Masks unauthorized data and clearly marks mock results as simulated.
    - Creates an immutable AuditEvent on every lookup.
    """
    record = _resolve_student_record(db, student_ref, current_user)

    # Perform inquiry via adapter
    adapter = get_apaar_adapter()
    if simulate_outage and hasattr(adapter, "simulate_outage"):
        adapter.simulate_outage = True

    result = adapter.verify(
        apaar_id=record.apaar_id or "",
        student_name=record.student_name,
        institution_id=record.institution_id
    )

    # Record verification attempt in database
    attempt = VerificationAttempt(
        record_id=record.id,
        apaar_id=record.apaar_id or "",
        provider=result.provider,
        outcome=result.outcome,
        reference_id=result.reference_id,
        details=result.details
    )
    db.add(attempt)

    # Audit log the inquiry
    audit = AuditEvent(
        actor_user_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role.value,
        institution_id=record.institution_id,
        action=AuditAction.VERIFICATION_LOOKUP,
        object_type="STUDENT_RECORD",
        object_id=record.id,
        outcome="SUCCESS",
        details=f"Verification lookup: Outcome={result.outcome.value}, Provider={result.provider}, Ref={result.reference_id}"
    )
    db.add(audit)
    db.commit()

    return result

@router.get("/{student_ref}/certificate", summary="Synthetic degree certificate preview with APAAR and Student ID display (Brief Section 2 & 10)")
def get_student_certificate_preview(
    student_ref: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate synthetic certificate preview data displaying APAAR ID alongside institution Student ID
    for degree-awarding bodies per Brief Section 2 (R16) and Section 10.
    Clearly marked as synthetic prototype display.
    """
    record = _resolve_student_record(db, student_ref, current_user)

    from backend.app.models.institution import Institution, Programme
    inst = db.query(Institution).filter(Institution.id == record.institution_id).first()
    prog = db.query(Programme).filter(Programme.id == record.programme_id).first()

    return {
        "is_synthetic_preview": True,
        "disclaimer": "SYNTHETIC PROTOTYPE PREVIEW ONLY — NOT AN OFFICIAL LEGAL CREDENTIAL",
        "institution_name": inst.name if inst else "AICTE Approved Institution",
        "institution_code": inst.code if inst else "AICTE-INST",
        "student_name": record.student_name or "Synthetic Student",
        "institution_student_id": record.institution_student_id,
        "apaar_id": record.apaar_id or "NOT_ASSIGNED",
        "programme_name": prog.name if prog else "Technical Programme",
        "academic_year": record.academic_year,
        "seat_type": record.seat_type.value,
        "enrolment_status": record.enrolment_status.value,
        "verification_reference": f"CERT-PREV-{record.id[:8].upper()}"
    }
