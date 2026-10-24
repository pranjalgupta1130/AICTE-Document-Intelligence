from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.errors import PermissionDeniedError
from backend.app.core.permissions import get_current_user
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
