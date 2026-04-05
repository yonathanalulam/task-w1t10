from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import secrets

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import hash_token
from app.models.auth import Session as AuthSession
from app.models.user import User
from app.services.authorization import user_has_any_permission
from app.services.auth import get_active_api_token, get_active_session, has_recent_step_up


def db_dep(db: Session = Depends(get_db)) -> Session:
    return db


def current_session_dep(
    db: Session = Depends(db_dep),
    session_cookie: str | None = Cookie(default=None, alias=get_settings().session_cookie_name),
) -> AuthSession:
    if not session_cookie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing session")

    session = get_active_session(db, session_cookie)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    return session


def require_roles(*required_roles: str) -> Callable[[AuthSession], AuthSession]:
    def dep(auth_session: AuthSession = Depends(current_session_dep)) -> AuthSession:
        user_roles = {user_role.role.name for user_role in auth_session.user.user_roles}
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return auth_session

    return dep


def require_recent_step_up(auth_session: AuthSession = Depends(current_session_dep)) -> AuthSession:
    if not has_recent_step_up(auth_session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Step-up authentication required",
        )
    return auth_session


def _ensure_permissions(db: Session, auth_session: AuthSession, *required_permissions: str) -> AuthSession:
    if not user_has_any_permission(db, user_id=auth_session.user_id, required_permissions=required_permissions):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permission")
    return auth_session


def org_admin_session_dep(
    auth_session: AuthSession = Depends(current_session_dep),
    db: Session = Depends(db_dep),
) -> AuthSession:
    return _ensure_permissions(db, auth_session, "org.manage")


def csrf_protected_session_dep(
    request: Request,
    auth_session: AuthSession = Depends(current_session_dep),
    csrf_cookie: str | None = Cookie(default=None, alias=get_settings().csrf_cookie_name),
) -> AuthSession:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return auth_session

    csrf_header = request.headers.get(get_settings().csrf_header_name)
    if not csrf_cookie or not csrf_header:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token missing")

    if not secrets.compare_digest(csrf_cookie, csrf_header):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token mismatch")

    if not secrets.compare_digest(hash_token(csrf_header), auth_session.csrf_token_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token invalid")

    return auth_session


def org_admin_csrf_session_dep(
    auth_session: AuthSession = Depends(csrf_protected_session_dep),
    db: Session = Depends(db_dep),
) -> AuthSession:
    return _ensure_permissions(db, auth_session, "org.manage")


def auditor_session_dep(
    auth_session: AuthSession = Depends(current_session_dep),
    db: Session = Depends(db_dep),
) -> AuthSession:
    return _ensure_permissions(db, auth_session, "org.manage", "audit.read")


def planner_session_dep(
    auth_session: AuthSession = Depends(current_session_dep),
    db: Session = Depends(db_dep),
) -> AuthSession:
    return _ensure_permissions(db, auth_session, "org.manage", "itinerary.write")


def planner_csrf_session_dep(
    auth_session: AuthSession = Depends(csrf_protected_session_dep),
    db: Session = Depends(db_dep),
) -> AuthSession:
    return _ensure_permissions(db, auth_session, "org.manage", "itinerary.write")


@dataclass(slots=True)
class PlannerActor:
    user: User
    auth_mode: str


def _ensure_user_permissions(db: Session, user: User, *required_permissions: str) -> None:
    if not user_has_any_permission(db, user_id=user.id, required_permissions=required_permissions):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permission")


def planner_sync_actor_dep(
    request: Request,
    db: Session = Depends(db_dep),
    session_cookie: str | None = Cookie(default=None, alias=get_settings().session_cookie_name),
    csrf_cookie: str | None = Cookie(default=None, alias=get_settings().csrf_cookie_name),
) -> PlannerActor:
    authorization = request.headers.get("Authorization")
    if authorization and authorization.lower().startswith("bearer "):
        raw_token = authorization[7:].strip()
        if not raw_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API token")

        api_token = get_active_api_token(db, raw_token)
        if not api_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API token")

        _ensure_user_permissions(db, api_token.user, "org.manage", "itinerary.write")
        return PlannerActor(user=api_token.user, auth_mode="api_token")

    if not session_cookie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing session")

    auth_session = get_active_session(db, session_cookie)
    if not auth_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    _ensure_user_permissions(db, auth_session.user, "org.manage", "itinerary.write")

    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        csrf_header = request.headers.get(get_settings().csrf_header_name)
        if not csrf_cookie or not csrf_header:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token missing")
        if not secrets.compare_digest(csrf_cookie, csrf_header):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token mismatch")
        if not secrets.compare_digest(hash_token(csrf_header), auth_session.csrf_token_hash):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token invalid")

    return PlannerActor(user=auth_session.user, auth_mode="session")
