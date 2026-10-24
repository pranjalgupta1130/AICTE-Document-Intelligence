import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.api.v1.router import api_router
from backend.app.core.config import settings
from backend.app.core.errors import AppException, make_error_response
from backend.app.db.session import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database schema is initialized on startup
    init_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API for AICTE APAAR Student Data Management & Verification Platform (SIH 26263)",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID Middleware
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or f"req-{uuid.uuid4().hex[:12]}"
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# Standardized Error Handlers
@app.exception_handler(AppException)
async def handle_app_exception(request: Request, exc: AppException):
    req_id = getattr(request.state, "request_id", None)
    return make_error_response(
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        request_id=req_id
    )

@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    req_id = getattr(request.state, "request_id", None)
    # Sanitize validation details
    errors = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        errors.append({"field": loc, "issue": err.get("msg")})
    return make_error_response(
        code="VALIDATION_ERROR",
        message="Request payload or parameters failed validation.",
        status_code=422,
        details=errors,
        request_id=req_id
    )

@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(request: Request, exc: StarletteHTTPException):
    req_id = getattr(request.state, "request_id", None)
    code = "RESOURCE_NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
    return make_error_response(
        code=code,
        message=str(exc.detail),
        status_code=exc.status_code,
        request_id=req_id
    )

@app.exception_handler(Exception)
async def handle_generic_exception(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", None)
    # Never leak stack traces in client response per security requirements
    return make_error_response(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred. Please contact system support.",
        status_code=500,
        request_id=req_id
    )

# Direct root health endpoint for orchestrators / probes
from backend.app.api.v1.health import router as health_router
app.include_router(health_router, prefix="")

# Versioned API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
