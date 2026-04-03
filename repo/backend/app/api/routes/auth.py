from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import csrf_protected_session_dep, current_session_dep, db_dep
from app.core.config import get_settings
from app.core.security import create_random_secret, load_or_create_token_key, verify_password
from app.models.auth import Session as AuthSession
from app.schemas.auth import (
    ApiTokenCreated,
    ApiTokenListItem,
    AuthResponse,
    LoginRequest,
    StepUpRequest,
    TokenCreateRequest,
)
from app.services.auth import (
    authenticate_user,
    create_api_token,
    create_browser_session,
    list_api_tokens,
    mark_step_up,
    revoke_api_token,
    revoke_session,
    serialize_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(db_dep)) -> AuthResponse:
    user = authenticate_user(db, payload.org_slug, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    raw_session_token = create_random_secret(32)
    raw_csrf_token = create_random_secret(24)
    auth_session = create_browser_session(db, user, raw_session_token, raw_csrf_token)
    settings = get_settings()

    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_session_token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="strict",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=raw_csrf_token,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite="strict",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )

    return AuthResponse(user=serialize_user(auth_session))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    auth_session: AuthSession = Depends(csrf_protected_session_dep),
    db: Session = Depends(db_dep),
) -> None:
    revoke_session(db, auth_session)
    settings = get_settings()
    response.delete_cookie(key=settings.session_cookie_name, path="/")
    response.delete_cookie(key=settings.csrf_cookie_name, path="/")


@router.get("/me", response_model=AuthResponse)
def me(auth_session: AuthSession = Depends(current_session_dep)) -> AuthResponse:
    return AuthResponse(user=serialize_user(auth_session))


@router.post("/step-up", response_model=AuthResponse)
def step_up(
    payload: StepUpRequest,
    auth_session: AuthSession = Depends(csrf_protected_session_dep),
    db: Session = Depends(db_dep),
) -> AuthResponse:
    if not verify_password(payload.password, auth_session.user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")

    refreshed = mark_step_up(db, auth_session)
    return AuthResponse(user=serialize_user(refreshed))


@router.post("/tokens", response_model=ApiTokenCreated, status_code=status.HTTP_201_CREATED)
def create_token(
    payload: TokenCreateRequest,
    auth_session: AuthSession = Depends(csrf_protected_session_dep),
    db: Session = Depends(db_dep),
) -> ApiTokenCreated:
    raw_token = create_random_secret(40)
    key = load_or_create_token_key(get_settings().token_encryption_key_path)
    token = create_api_token(
        db,
        user=auth_session.user,
        label=payload.label,
        raw_token=raw_token,
        encryption_key=key,
        expires_in_days_override=payload.expires_in_days,
    )

    return ApiTokenCreated(
        id=token.id,
        label=token.label,
        expires_at=token.expires_at,
        token=raw_token,
    )


@router.get("/tokens", response_model=list[ApiTokenListItem])
def list_tokens(
    auth_session: AuthSession = Depends(current_session_dep),
    db: Session = Depends(db_dep),
) -> list[ApiTokenListItem]:
    tokens = list_api_tokens(db, user_id=auth_session.user_id)
    return [
        ApiTokenListItem(
            id=token.id,
            label=token.label,
            expires_at=token.expires_at,
            revoked_at=token.revoked_at,
            last_used_at=token.last_used_at,
        )
        for token in tokens
    ]


@router.delete("/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_token(
    token_id: str,
    auth_session: AuthSession = Depends(csrf_protected_session_dep),
    db: Session = Depends(db_dep),
) -> None:
    deleted = revoke_api_token(db, user_id=auth_session.user_id, token_id=token_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
