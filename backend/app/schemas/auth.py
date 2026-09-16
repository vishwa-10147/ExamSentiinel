from typing import Optional
import uuid
from pydantic import BaseModel, Field
from app.schemas.user import UserResponse


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(default=1800, description="Access token lifetime in seconds")
    user: UserResponse


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class TokenPayload(BaseModel):
    user_id: uuid.UUID
    email: str
    role: str
    institution_id: Optional[uuid.UUID] = None
    type: str
    exp: int
    iat: int
    jti: Optional[str] = None
