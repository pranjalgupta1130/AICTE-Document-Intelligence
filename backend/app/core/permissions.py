from typing import Callable, List, Optional
from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session
import jwt

from backend.app.core.errors import AppException, AuthenticationError, PermissionDeniedError, InstitutionScopeError
from backend.app.core.security import decode_access_token
from backend.app.db.session import get_db
from backend.app.models.enums import UserRole
from backend.app.models.user import User

def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
) -> User:
    """
    Extract and validate Bearer JWT token from Authorization header and fetch User.
    """
    if not authorization:
        raise AppException(
            code="AUTHENTICATION_REQUIRED",
            message="Authorization bearer token is required",
            status_code=401
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AppException(
            code="AUTHENTICATION_FAILED",
            message="Invalid authorization header format. Expected 'Bearer <token>'",
            status_code=401
        )

    token = parts[1]
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Session token has expired. Please log in again.")
    except jwt.PyJWTError:
        raise AuthenticationError("Invalid or malformed session token.")

    user_id = payload.get("user_id") or payload.get("sub")
    if not user_id:
        raise AuthenticationError("Token payload is missing user subject identification.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # Check by email as fallback
        user = db.query(User).filter(User.email == user_id).first()

    if not user or not user.is_active:
        raise AuthenticationError("User account not found or deactivated.")

    return user

def require_roles(*allowed_roles: UserRole) -> Callable:
    """
    Dependency factory to enforce server-side RBAC on routes.
    """
    def role_dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
            allowed_vals = [r.value if hasattr(r, "value") else str(r) for r in allowed_roles]
            raise PermissionDeniedError(
                f"Role '{role_val}' is unauthorized. Required role in: {', '.join(allowed_vals)}"
            )
        return current_user
    return role_dependency

def enforce_institution_scope(
    current_user: User,
    requested_institution_id: Optional[str] = None
) -> Optional[str]:
    """
    Validates and enforces strict server-side institution data boundary.
    - AICTE_ADMIN and DEMO_ADMIN can access all institutions or filter by requested_institution_id.
    - INSTITUTION_ADMIN and INSTITUTION_OPERATOR can ONLY access their own institution.
    """
    if current_user.role in (UserRole.AICTE_ADMIN, UserRole.DEMO_ADMIN):
        return requested_institution_id

    # Institution roles must have a configured institution_id
    if not current_user.institution_id:
        raise InstitutionScopeError("Caller is an institution account but has no bound institution ID.")

    # Cross-institution access check
    if requested_institution_id and requested_institution_id != current_user.institution_id:
        raise InstitutionScopeError(
            f"Cross-institution access denied. Caller bound to '{current_user.institution_id}' "
            f"cannot access records of '{requested_institution_id}'."
        )

    return current_user.institution_id
