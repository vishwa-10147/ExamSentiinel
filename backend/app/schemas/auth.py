from typing import Optional
import uuid
from pydantic import BaseModel, Field
from app.schemas.user import UserResponse


class TokenResponse(BaseModel):
    # Omitted (null) for browsers using httpOnly cookie sessions; see app/core/auth_cookies.py.
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = Field(default=1800, description="Access token lifetime in seconds")
    user: UserResponse


class TokenRefreshRequest(BaseModel):
    # Optional for browsers: the refresh token then comes from the httpOnly cookie.
    refresh_token: Optional[str] = None


class TokenPayload(BaseModel):
    user_id: uuid.UUID
    email: str
    role: str
    institution_id: Optional[uuid.UUID] = None
    type: str
    exp: int
    iat: int
    jti: Optional[str] = None
