from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.errors import AuthenticationError
from backend.app.core.permissions import get_current_user
from backend.app.core.security import hash_password, verify_password, create_access_token
from backend.app.db.session import get_db
from backend.app.models.audit import AuditEvent
from backend.app.models.enums import AuditAction, UserRole
from backend.app.models.user import User
from backend.app.schemas.auth import LoginRequest, TokenResponse, UserRead

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user with email and salted password. Returns signed JWT bearer token.
    """
    user = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        # Record failed audit attempt
        audit = AuditEvent(
            actor_user_id=user.id if user else None,
            actor_email=payload.email,
            actor_role=user.role.value if user else "UNKNOWN",
            institution_id=user.institution_id if user else None,
            action=AuditAction.LOGIN,
            object_type="USER",
            object_id=user.id if user else None,
            outcome="FAILURE",
            details="Invalid credentials provided"
        )
        db.add(audit)
        db.commit()
        raise AuthenticationError("Invalid email or password.")

    if not user.is_active:
        raise AuthenticationError("User account has been deactivated.")

    # Record successful login audit
    audit = AuditEvent(
        actor_user_id=user.id,
        actor_email=user.email,
        actor_role=user.role.value,
        institution_id=user.institution_id,
        action=AuditAction.LOGIN,
        object_type="USER",
        object_id=user.id,
        outcome="SUCCESS",
        details="Interactive session initiated"
    )
    db.add(audit)
    db.commit()

    token = create_access_token(
        subject=user.email,
        role=user.role.value,
        institution_id=user.institution_id,
        user_id=user.id
    )

    institution_name = user.institution.name if user.institution else None

    user_read = UserRead(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        institution_id=user.institution_id,
        institution_name=institution_name,
        is_active=user.is_active
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_read
    )

@router.get("/me", response_model=UserRead)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Return currently authenticated user profile and permissions scope.
    """
    institution_name = current_user.institution.name if current_user.institution else None
    return UserRead(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        institution_id=current_user.institution_id,
        institution_name=institution_name,
        is_active=current_user.is_active
    )
