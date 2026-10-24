from fastapi import APIRouter

from backend.app.api.v1.auth import router as auth_router, get_current_user_profile
from backend.app.api.v1.institutions import router as institutions_router
from backend.app.api.v1.intake import router as intake_router
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.imports import router as imports_router
from backend.app.api.v1.batches import router as batches_router
from backend.app.api.v1.reviews import router as reviews_router
from backend.app.api.v1.dashboard import router as dashboard_router
from backend.app.api.v1.verification import router as verification_router
from backend.app.api.v1.reports import router as reports_router
from backend.app.schemas.auth import UserRead

api_router = APIRouter()

# Core user profile route matching SIH26263 Brief Section 9 (GET /api/v1/me)
api_router.add_api_route(
    "/me",
    get_current_user_profile,
    methods=["GET"],
    response_model=UserRead,
    tags=["Authentication"],
    summary="Get current user profile (Brief Section 9 Contract)"
)

api_router.include_router(auth_router)
api_router.include_router(institutions_router)
api_router.include_router(intake_router)
api_router.include_router(imports_router)
api_router.include_router(batches_router)
api_router.include_router(reviews_router)
api_router.include_router(dashboard_router)
api_router.include_router(verification_router)
api_router.include_router(reports_router)
api_router.include_router(health_router)
