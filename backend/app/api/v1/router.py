from fastapi import APIRouter

from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.institutions import router as institutions_router
from backend.app.api.v1.intake import router as intake_router
from backend.app.api.v1.health import router as health_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(institutions_router)
api_router.include_router(intake_router)
api_router.include_router(health_router)
