from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    org_slug: str = Field(min_length=1, max_length=100)
    username: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=8, max_length=256)


class StepUpRequest(BaseModel):
    password: str = Field(min_length=8, max_length=256)


class TokenCreateRequest(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    expires_in_days: int | None = Field(default=None, ge=1, le=365)


class AuthUser(BaseModel):
    id: str
    username: str
    org_id: str
    org_slug: str
    roles: list[str]
    step_up_valid_until: datetime | None


class AuthResponse(BaseModel):
    user: AuthUser


class ApiTokenCreated(BaseModel):
    id: str
    label: str
    expires_at: datetime
    token: str


class ApiTokenListItem(BaseModel):
    id: str
    label: str
    expires_at: datetime
    revoked_at: datetime | None
    last_used_at: datetime | None
