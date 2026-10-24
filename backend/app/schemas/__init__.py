from backend.app.schemas.auth import LoginRequest, UserRead, TokenResponse
from backend.app.schemas.institution import InstitutionRead, ProgrammeRead, ApprovedIntakeRead
from backend.app.schemas.common import PaginatedList, HealthResponse, ErrorDetail, ErrorEnvelope

__all__ = [
    "LoginRequest",
    "UserRead",
    "TokenResponse",
    "InstitutionRead",
    "ProgrammeRead",
    "ApprovedIntakeRead",
    "PaginatedList",
    "HealthResponse",
    "ErrorDetail",
    "ErrorEnvelope",
]
