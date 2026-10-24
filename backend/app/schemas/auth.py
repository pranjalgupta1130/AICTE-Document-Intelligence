from typing import Optional
from pydantic import BaseModel, ConfigDict
from backend.app.models.enums import UserRole

class LoginRequest(BaseModel):
    email: str
    password: str

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    role: UserRole
    institution_id: Optional[str] = None
    institution_name: Optional[str] = None
    is_active: bool

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    user: UserRead
