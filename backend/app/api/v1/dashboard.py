from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.core.permissions import get_current_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.workflows import (
    InstitutionDashboardMetrics,
    AICTEDashboardMetrics,
)
from backend.app.services.workflow_service import (
    get_institution_dashboard,
    get_aicte_dashboard,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/institution", response_model=InstitutionDashboardMetrics, summary="Get institution operational dashboard metrics")
def institution_dashboard_endpoint(
    institution_id: Optional[str] = Query(None, description="Optional institution ID (strictly scoped to user unless AICTE admin)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve operational intake and validation metrics for the current institution.
    Enforces strict institution isolation.
    """
    return get_institution_dashboard(
        db=db,
        current_user=current_user,
        institution_id=institution_id
    )

@router.get("/aicte", response_model=AICTEDashboardMetrics, summary="Get AICTE national analytics and aggregate intake dashboard")
def aicte_dashboard_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve national aggregate metrics across all AICTE-approved institutions.
    Strictly restricted to AICTE_ADMIN and DEMO_ADMIN.
    """
    return get_aicte_dashboard(
        db=db,
        current_user=current_user
    )
