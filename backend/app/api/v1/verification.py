"""
Verification API Router.
Handles privacy-preserving, purpose-restricted single-record verification lookup.
Uses replaceable APAAR adapter provider and logs immutable audit records.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.adapters import get_apaar_adapter, VerificationResult
from backend.app.core.errors import NotFoundError, PermissionDeniedError
from backend.app.core.permissions import get_current_user, enforce_institution_scope
from backend.app.db.session import get_db
from backend.app.models.audit import AuditEvent
from backend.app.models.enums import AuditAction, UserRole
from backend.app.models.institution import Institution, Programme
from backend.app.models.student import StudentRecord
from backend.app.models.user import User
from backend.app.models.verification import VerificationAttempt

router = APIRouter(prefix="/verification", tags=["Verification"])

class StudentSearchResult(BaseModel):
    id: str
    institution_id: str
    institution_name: Optional[str] = None
    institution_code: Optional[str] = None
    institution_student_id: str
    student_name: Optional[str] = None
    apaar_id: Optional[str] = None
    academic_year: str
    programme_id: str
    programme_name: Optional[str] = None
    enrolment_status: str
    seat_type: str

class StudentSearchResponse(BaseModel):
    items: List[StudentSearchResult]
    total: int


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
      2. If queried by domain identifier (apaar_id or institution_student_id) or student_name,
         filters strictly by current_user.institution_id so cross-institution duplicates
         resolve safely to the caller's own record without collision or information leakage.
    """
    is_privileged = current_user.role in (
        UserRole.AICTE_ADMIN,
        UserRole.DEMO_ADMIN,
        UserRole.EXTERNAL_VERIFIER
    )

    clean_ref = student_ref.replace("-", "").strip()

    if is_privileged:
        record = db.query(StudentRecord).filter(
            (StudentRecord.id == student_ref) |
            (StudentRecord.institution_student_id == student_ref) |
            (StudentRecord.apaar_id == student_ref) |
            (StudentRecord.apaar_id == clean_ref) |
            (StudentRecord.student_name.ilike(student_ref)) |
            (StudentRecord.student_name.ilike(f"%{student_ref}%"))
        ).order_by(StudentRecord.id.asc()).first()
    else:
        inst_id = current_user.institution_id
        if not inst_id:
            raise NotFoundError(f"Student record '{student_ref}' not found.")

        # First, check if student_ref is a record in caller's institution
        record = db.query(StudentRecord).filter(
            StudentRecord.institution_id == inst_id,
            (
                (StudentRecord.id == student_ref) |
                (StudentRecord.institution_student_id == student_ref) |
                (StudentRecord.apaar_id == student_ref) |
                (StudentRecord.apaar_id == clean_ref) |
                (StudentRecord.student_name.ilike(student_ref)) |
                (StudentRecord.student_name.ilike(f"%{student_ref}%"))
            )
        ).order_by(StudentRecord.id.asc()).first()

        # If not found in caller's institution, check if student_ref is a direct primary key (id)
        # of another institution's record. If so, enforce institution scope to return 403.
        if not record:
            cross_record = db.query(StudentRecord).filter(StudentRecord.id == student_ref).first()
            if cross_record:
                enforce_institution_scope(current_user, cross_record.institution_id)

    if not record:
        raise NotFoundError(f"Student record '{student_ref}' not found.")

    if not is_privileged:
        enforce_institution_scope(current_user, record.institution_id)

    return record


@router.get("/search", response_model=StudentSearchResponse, summary="Search student records with institution isolation and APAAR masking")
def search_student_records(
    q: Optional[str] = Query(None, description="Search term for student name, roll number, or APAAR"),
    academic_year: Optional[str] = Query(None, description="Filter by academic year"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Search student records with strict institution-level authorization and role-based APAAR masking.
    - AICTE_ADMIN / DEMO_ADMIN can view records across all institutions.
    - INSTITUTION_ADMIN / INSTITUTION_OPERATOR can only view records from their authorized institution.
    - EXTERNAL_VERIFIER cannot enumerate or search whole student sets.
    """
    if current_user.role == UserRole.EXTERNAL_VERIFIER:
        raise PermissionDeniedError("External Verifiers cannot enumerate or search bulk student records.")

    query = db.query(StudentRecord)

    # Institution scope
    if current_user.role in (UserRole.INSTITUTION_ADMIN, UserRole.INSTITUTION_OPERATOR):
        if not current_user.institution_id:
            return StudentSearchResponse(items=[], total=0)
        query = query.filter(StudentRecord.institution_id == current_user.institution_id)

    if academic_year:
        query = query.filter(StudentRecord.academic_year == academic_year)

    if q and q.strip():
        clean_q = q.strip()
        clean_digits = clean_q.replace("-", "")
        conditions = [
            StudentRecord.institution_student_id.ilike(f"%{clean_q}%"),
            StudentRecord.student_name.ilike(f"%{clean_q}%"),
            StudentRecord.id == clean_q,
        ]
        if clean_digits:
            conditions.append(StudentRecord.apaar_id.ilike(f"%{clean_digits}%"))
            conditions.append(StudentRecord.apaar_id.ilike(f"%{clean_q}%"))
        query = query.filter(or_(*conditions))

    total = query.count()
    records = query.order_by(StudentRecord.academic_year.desc(), StudentRecord.institution_student_id.asc()).offset(offset).limit(limit).all()

    can_view_unmasked = current_user.role in (UserRole.AICTE_ADMIN, UserRole.DEMO_ADMIN, UserRole.INSTITUTION_ADMIN)

    # Batch load institutions and programmes for fast mapping
    inst_ids = {r.institution_id for r in records}
    prog_ids = {r.programme_id for r in records}

    institutions = {i.id: i for i in db.query(Institution).filter(Institution.id.in_(inst_ids)).all()} if inst_ids else {}
    programmes = {p.id: p for p in db.query(Programme).filter(Programme.id.in_(prog_ids)).all()} if prog_ids else {}

    items = []
    for r in records:
        inst = institutions.get(r.institution_id)
        prog = programmes.get(r.programme_id)

        masked_apaar = r.apaar_id
        if masked_apaar and not can_view_unmasked:
            clean = masked_apaar.replace("-", "")
            if len(clean) >= 12:
                masked_apaar = f"{clean[:4]}-XXXX-{clean[-4:]}"

        items.append(
            StudentSearchResult(
                id=r.id,
                institution_id=r.institution_id,
                institution_name=inst.name if inst else None,
                institution_code=inst.code if inst else None,
                institution_student_id=r.institution_student_id,
                student_name=r.student_name,
                apaar_id=masked_apaar,
                academic_year=r.academic_year,
                programme_id=r.programme_id,
                programme_name=prog.name if prog else None,
                enrolment_status=r.enrolment_status.value,
                seat_type=r.seat_type.value
            )
        )

    return StudentSearchResponse(items=items, total=total)


@router.get("/{student_ref}", response_model=VerificationResult, summary="Privacy-restricted single-record APAAR verification lookup")
def verify_student_record(
    student_ref: str,
    simulate_outage: bool = Query(False, description="Simulate provider outage for testing graceful degradation"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Perform a purpose-restricted, privacy-preserving verification check for a student.
    - Can look up by student_id, institution_student_id, apaar_id, or student_name.
    - Enriches response with real student and institution context.
    - Masks unauthorized data and clearly marks mock results as simulated.
    - Creates an immutable AuditEvent on every lookup and returns real audit trail.
    """
    record = _resolve_student_record(db, student_ref, current_user)

    inst = db.query(Institution).filter(Institution.id == record.institution_id).first()
    prog = db.query(Programme).filter(Programme.id == record.programme_id).first()

    # Perform inquiry via adapter
    adapter = get_apaar_adapter()
    if simulate_outage and hasattr(adapter, "simulate_outage"):
        adapter.simulate_outage = True

    result = adapter.verify(
        apaar_id=record.apaar_id or "",
        student_name=record.student_name,
        institution_id=record.institution_id
    )

    # Enrich contextual fields
    result.record_id = record.id
    result.institution_student_id = record.institution_student_id
    result.institution_name = inst.name if inst else "AICTE Approved Institution"
    result.institution_code = inst.code if inst else "AICTE-INST"
    result.programme_id = record.programme_id
    result.programme_name = prog.name if prog else "Technical Programme"
    result.academic_year = record.academic_year
    result.enrolment_status = record.enrolment_status.value
    result.seat_type = record.seat_type.value

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

    # Retrieve real audit history for this student record
    past_audits = db.query(AuditEvent).filter(
        (AuditEvent.object_id == record.id) |
        (AuditEvent.details.contains(record.institution_student_id))
    ).order_by(AuditEvent.timestamp.desc()).limit(15).all()

    trail = []
    for ev in past_audits:
        trail.append({
            "timestamp": ev.timestamp.strftime("%d %b %Y, %H:%M:%S UTC"),
            "eventType": ev.action.value.replace("_", " ").title(),
            "actor": f"{ev.actor_email} ({ev.actor_role})",
            "actionDetails": ev.details or f"Action {ev.action.value} on record",
            "complianceStatus": ev.outcome,
            "complianceBadgeClass": "bg-status-verified-surface text-status-verified border-status-verified-border" if ev.outcome == "SUCCESS" else "bg-status-error-surface text-status-error border-status-error-border"
        })
    result.audit_trail = trail

    # Apply APAAR masking for non-administrative roles
    can_view_unmasked = current_user.role in (UserRole.AICTE_ADMIN, UserRole.DEMO_ADMIN, UserRole.INSTITUTION_ADMIN)
    if result.apaar_id and not can_view_unmasked:
        clean = result.apaar_id.replace("-", "")
        if len(clean) >= 12:
            result.apaar_id = f"{clean[:4]}-XXXX-{clean[-4:]}"

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
    Clearly marked as synthetic prototype display with role-based APAAR masking.
    """
    record = _resolve_student_record(db, student_ref, current_user)

    inst = db.query(Institution).filter(Institution.id == record.institution_id).first()
    prog = db.query(Programme).filter(Programme.id == record.programme_id).first()

    can_view_unmasked = current_user.role in (UserRole.AICTE_ADMIN, UserRole.DEMO_ADMIN, UserRole.INSTITUTION_ADMIN)
    apaar_val = record.apaar_id or "NOT_ASSIGNED"
    if apaar_val != "NOT_ASSIGNED" and not can_view_unmasked:
        clean = apaar_val.replace("-", "")
        if len(clean) >= 12:
            apaar_val = f"{clean[:4]}-XXXX-{clean[-4:]}"

    return {
        "is_synthetic_preview": True,
        "disclaimer": "SYNTHETIC PROTOTYPE PREVIEW ONLY — NOT AN OFFICIAL LEGAL CREDENTIAL",
        "institution_name": inst.name if inst else "AICTE Approved Institution",
        "institution_code": inst.code if inst else "AICTE-INST",
        "student_name": record.student_name or "Synthetic Student",
        "institution_student_id": record.institution_student_id,
        "apaar_id": apaar_val,
        "programme_name": prog.name if prog else "Technical Programme",
        "academic_year": record.academic_year,
        "seat_type": record.seat_type.value,
        "enrolment_status": record.enrolment_status.value,
        "verification_reference": f"CERT-PREV-{record.id[:8].upper()}"
    }
