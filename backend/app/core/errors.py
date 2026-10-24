import uuid
from typing import Any, Optional
from fastapi import Request
from fastapi.responses import JSONResponse

class AppException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Any] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)

class AuthenticationError(AppException):
    def __init__(self, message: str = "Invalid authentication credentials", details: Optional[Any] = None):
        super().__init__(
            code="AUTHENTICATION_FAILED",
            message=message,
            status_code=401,
            details=details
        )

class PermissionDeniedError(AppException):
    def __init__(self, message: str = "Permission denied for this resource", details: Optional[Any] = None):
        super().__init__(
            code="PERMISSION_DENIED",
            message=message,
            status_code=403,
            details=details
        )

class InstitutionScopeError(AppException):
    def __init__(self, message: str = "Access to records of other institutions is strictly prohibited", details: Optional[Any] = None):
        super().__init__(
            code="INSTITUTION_SCOPE_VIOLATION",
            message=message,
            status_code=403,
            details=details
        )

class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found", details: Optional[Any] = None):
        super().__init__(
            code="RESOURCE_NOT_FOUND",
            message=message,
            status_code=404,
            details=details
        )

def make_error_response(
    code: str,
    message: str,
    status_code: int = 400,
    details: Optional[Any] = None,
    request_id: Optional[str] = None
) -> JSONResponse:
    req_id = request_id or f"req-{uuid.uuid4().hex[:12]}"
    content = {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": req_id
        }
    }
    return JSONResponse(status_code=status_code, content=content)
