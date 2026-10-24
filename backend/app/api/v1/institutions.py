from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.core.errors import NotFoundError, PermissionDeniedError
from backend.app.core.permissions import get_current_user, enforce_institution_scope
from backend.app.db.session import get_db
from backend.app.models.enums import UserRole
from backend.app.models.institution import Institution
from backend.app.models.user import User
from backend.app.schemas.common import PaginatedList
from backend.app.schemas.institution import InstitutionRead

router = APIRouter(prefix="/institutions", tags=["Institutions"])

@router.get("", response_model=PaginatedList[InstitutionRead])
def list_institutions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List institutions accessible by caller.
    - AICTE_ADMIN and DEMO_ADMIN can view all institutions.
    - INSTITUTION_ADMIN and INSTITUTION_OPERATOR are strictly scoped to their own institution.
    """
    if current_user.role == UserRole.EXTERNAL_VERIFIER:
        raise PermissionDeniedError("External Verifiers do not have permission to browse institutions.")

    query = db.query(Institution)

    # Apply strict institution isolation for institution accounts
    if current_user.role in (UserRole.INSTITUTION_ADMIN, UserRole.INSTITUTION_OPERATOR):
        query = query.filter(Institution.id == current_user.institution_id)

    institutions = query.order_by(Institution.name).all()

    items = [
        InstitutionRead(
            id=inst.id,
            name=inst.name,
            code=inst.code,
            state=inst.state,
            status=inst.status
        )
        for inst in institutions
    ]
    return PaginatedList[InstitutionRead](items=items, total=len(items))

@router.get("/{institution_id}/quality-summary", summary="Get aggregated institution data quality score across batches")
def get_institution_quality_summary(
    institution_id: str,
    academic_year: Optional[str] = Query(None, description="Filter by academic year"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve record-weighted data quality score aggregated across all batches of an institution.
    Enforces strict institution isolation.
    """
    enforce_institution_scope(current_user, institution_id)

    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise NotFoundError(f"Institution '{institution_id}' was not found.")

    from backend.app.services.quality_service import calculate_institution_quality_aggregation
    return calculate_institution_quality_aggregation(
        db=db,
        institution_id=institution_id,
        academic_year=academic_year
    )

@router.get("/{institution_id}/longitudinal-trends", summary="Get longitudinal data quality and enrolment trends across historical batches")
def get_institution_longitudinal_trends(
    institution_id: str,
    academic_year: Optional[str] = Query(None, description="Filter by academic year"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve longitudinal data quality and enrolment trends across historical batches for an institution.
    Provides batch timeline datapoints, score deltas, and net improvement tracking.
    Enforces strict institution isolation.
    """
    enforce_institution_scope(current_user, institution_id)

    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise NotFoundError(f"Institution '{institution_id}' was not found.")

    from backend.app.services.quality_service import calculate_institution_longitudinal_trends
    return calculate_institution_longitudinal_trends(
        db=db,
        institution_id=institution_id,
        academic_year=academic_year
    )
