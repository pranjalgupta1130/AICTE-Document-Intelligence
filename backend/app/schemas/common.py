from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class PaginatedList(BaseModel, Generic[T]):
    items: List[T]
    total: int

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    database: str

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None
    request_id: str

class ErrorEnvelope(BaseModel):
    error: ErrorDetail
