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

@router.get("/{student_ref}", response_model=VerificationResult, summary="Privacy-restricted single-record APAAR verification lookup")
def verify_student_record(
    student_ref: str,
    simulate_outage: bool = Query(False, description="Simulate provider outage for testing graceful degradation"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Perform a purpose-restricted, privacy-preserving verification check for a student.
    - Can look up by student_id or apaar_id.
    - Masks unauthorized data and clearly marks mock results as simulated.
    - Creates an immutable AuditEvent on every lookup.
    """
    # Look up student record by id, institution_student_id, or apaar_id
    record = db.query(StudentRecord).filter(
        (StudentRecord.id == student_ref) |
        (StudentRecord.institution_student_id == student_ref) |
        (StudentRecord.apaar_id == student_ref)
    ).first()

    if not record:
        raise NotFoundError(f"Student record '{student_ref}' not found.")

    # Enforce institution isolation unless AICTE/DEMO admin or external verifier
    if current_user.role not in (UserRole.AICTE_ADMIN, UserRole.DEMO_ADMIN, UserRole.EXTERNAL_VERIFIER):
        enforce_institution_scope(current_user, record.institution_id)

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
