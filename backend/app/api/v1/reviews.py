from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from backend.app.core.permissions import get_current_user
from backend.app.db.session import get_db
from backend.app.models.enums import MatchStatus, UserRole
from backend.app.models.match import MatchCandidate
from backend.app.models.student import StudentRecord
from backend.app.models.user import User
from backend.app.schemas.common import PaginatedList
from backend.app.schemas.workflows import (
    BatchReviewRequest,
    BatchReviewResponse,
    FindingReviewRequest,
    FindingReviewResponse,
    MatchCandidateReviewRequest,
)
from backend.app.schemas.validation import MatchCandidateRead
from backend.app.services.workflow_service import review_batch, review_finding, review_match_candidate

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.post("/batches/{batch_id}", response_model=BatchReviewResponse, summary="Review an institutional import batch")
def review_batch_endpoint(
    batch_id: str,
    payload: BatchReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Review and update status of an institutional import batch.
    Decisions: UNDER_REVIEW, ACCEPTED, REJECTED, NEEDS_CORRECTION.
    Restricted to AICTE administrators (AICTE_ADMIN, DEMO_ADMIN).
    """
    return review_batch(
        db=db,
        batch_id=batch_id,
        current_user=current_user,
        request=payload
    )


@router.post("/{finding_id}", response_model=FindingReviewResponse, summary="Review and resolve/dismiss a validation finding")
def review_finding_endpoint(
    finding_id: str,
    payload: FindingReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Review a specific validation finding.
    Allows institution administrators and operators to document remediation
    or dismiss explainable findings prior to batch submission.
    """
    return review_finding(
        db=db,
        finding_id=finding_id,
        current_user=current_user,
        request=payload
    )


@router.post("/matches/{match_id}", response_model=MatchCandidateRead, summary="Review a cross-institution duplicate match candidate")
def review_match_candidate_endpoint(
    match_id: str,
    payload: MatchCandidateReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Review a cross-institution duplicate match candidate.
    Restricted to AICTE administrators (AICTE_ADMIN, DEMO_ADMIN).
    """
    candidate = review_match_candidate(
        db=db,
        match_id=match_id,
        current_user=current_user,
        request=payload
    )
    db.refresh(candidate)
    return MatchCandidateRead.model_validate(candidate)


@router.get("/matches", response_model=PaginatedList[MatchCandidateRead], summary="List cross-institution match candidates")
def list_matches_endpoint(
    status: Optional[MatchStatus] = Query(None, description="Filter by review status"),
    institution_id: Optional[str] = Query(None, description="Filter by participating institution"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List cross-institution match candidates.
    - AICTE_ADMIN and DEMO_ADMIN can view all match candidates.
    - Institution users can only view match candidates involving their own institution.
    """
    query = db.query(MatchCandidate).options(
        joinedload(MatchCandidate.record_a).joinedload(StudentRecord.programme),
        joinedload(MatchCandidate.record_b).joinedload(StudentRecord.programme),
        joinedload(MatchCandidate.institution_a),
        joinedload(MatchCandidate.institution_b)
    )

    if current_user.role not in (UserRole.AICTE_ADMIN, UserRole.DEMO_ADMIN):
        # Strictly restricted to own institution candidates
        user_inst_id = current_user.institution_id
        query = query.filter(
            (MatchCandidate.institution_a_id == user_inst_id) |
            (MatchCandidate.institution_b_id == user_inst_id)
        )
    elif institution_id:
        query = query.filter(
            (MatchCandidate.institution_a_id == institution_id) |
            (MatchCandidate.institution_b_id == institution_id)
        )

    if status:
        query = query.filter(MatchCandidate.status == status)

    total = query.count()
    items = query.order_by(MatchCandidate.created_at.desc()).offset(offset).limit(limit).all()

    can_view_unmasked = current_user.role in (UserRole.AICTE_ADMIN, UserRole.DEMO_ADMIN, UserRole.INSTITUTION_ADMIN)
    result_items = []
    for m in items:
        cand = MatchCandidateRead.model_validate(m)
        if not can_view_unmasked:
            if cand.record_a and cand.record_a.apaar_id and len(cand.record_a.apaar_id) >= 12:
                cand.record_a.apaar_id = f"{cand.record_a.apaar_id[:4]}-XXXX-{cand.record_a.apaar_id[-4:]}"
            if cand.record_b and cand.record_b.apaar_id and len(cand.record_b.apaar_id) >= 12:
                cand.record_b.apaar_id = f"{cand.record_b.apaar_id[:4]}-XXXX-{cand.record_b.apaar_id[-4:]}"
        result_items.append(cand)

    return PaginatedList[MatchCandidateRead](items=result_items, total=total)
