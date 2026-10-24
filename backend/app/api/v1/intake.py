from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.core.permissions import get_current_user, enforce_institution_scope
from backend.app.db.session import get_db
from backend.app.models.institution import ApprovedIntake, Programme
from backend.app.models.user import User
from backend.app.schemas.common import PaginatedList
from backend.app.schemas.institution import ApprovedIntakeRead

router = APIRouter(prefix="/intake", tags=["Approved Intake"])

@router.get("", response_model=PaginatedList[ApprovedIntakeRead])
def get_approved_intake(
    institution_id: Optional[str] = Query(None, description="Filter by institution ID"),
    academic_year: Optional[str] = Query(None, description="Filter by academic year (e.g. 2026-2027)"),
    programme_id: Optional[str] = Query(None, description="Filter by programme ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Query AICTE approved regular and supernumerary intake.
    Enforces strict institution isolation for institution roles.
    """
    scoped_inst_id = enforce_institution_scope(current_user, institution_id)

    query = db.query(ApprovedIntake).join(Programme, ApprovedIntake.programme_id == Programme.id)

    if scoped_inst_id:
        query = query.filter(ApprovedIntake.institution_id == scoped_inst_id)
    if academic_year:
        query = query.filter(ApprovedIntake.academic_year == academic_year)
    if programme_id:
        query = query.filter(ApprovedIntake.programme_id == programme_id)

    results = query.order_by(ApprovedIntake.academic_year.desc(), Programme.name).all()

    items = [
        ApprovedIntakeRead(
            id=item.id,
            institution_id=item.institution_id,
            programme_id=item.programme_id,
            programme_name=item.programme.name if item.programme else None,
            academic_year=item.academic_year,
            regular_intake=item.regular_intake,
            supernumerary_intake=item.supernumerary_intake,
            total_approved_intake=item.regular_intake + item.supernumerary_intake,
            supernumerary_policy=item.supernumerary_policy
        )
        for item in results
    ]
    return PaginatedList[ApprovedIntakeRead](items=items, total=len(items))
