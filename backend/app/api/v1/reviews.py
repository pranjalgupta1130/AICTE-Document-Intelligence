from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.permissions import get_current_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.workflows import (
    FindingReviewRequest,
    FindingReviewResponse,
    MatchCandidateReviewRequest,
)
from backend.app.schemas.validation import MatchCandidateRead
from backend.app.services.workflow_service import review_finding, review_match_candidate

router = APIRouter(prefix="/reviews", tags=["Reviews"])

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
    return review_match_candidate(
        db=db,
        match_id=match_id,
        current_user=current_user,
        request=payload
    )

