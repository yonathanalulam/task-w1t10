from __future__ import annotations

from datetime import UTC, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.security import (
    encrypt_token,
    expires_in_days,
    expires_in_hours,
    hash_token,
    utcnow,
    verify_password,
)
from app.models.auth import ApiToken, Session as AuthSession
from app.models.organization import Organization
from app.models.rbac import UserRole
from app.models.user import User


def _user_roles(user: User) -> list[str]:
    return sorted([user_role.role.name for user_role in user.user_roles])


def authenticate_user(db: Session, org_slug: str, username: str, password: str) -> User | None:
    user = (
        db.execute(
            select(User)
            .join(Organization, User.org_id == Organization.id)
            .where(Organization.slug == org_slug, User.username == username, User.is_active.is_(True))
            .options(selectinload(User.organization), selectinload(User.user_roles).selectinload(UserRole.role))
        )
        .scalars()
        .first()
    )

    if not user:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


def create_browser_session(db: Session, user: User, token: str, csrf_token: str) -> AuthSession:
    settings = get_settings()
    now = utcnow()
    session = AuthSession(
        user_id=user.id,
        token_hash=hash_token(token),
        csrf_token_hash=hash_token(csrf_token),
        expires_at=expires_in_hours(settings.session_ttl_hours),
        last_seen_at=now,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_active_session(db: Session, raw_token: str) -> AuthSession | None:
    token_hash = hash_token(raw_token)
    now = utcnow()
    session = (
        db.execute(
            select(AuthSession)
            .join(User, AuthSession.user_id == User.id)
            .where(
                AuthSession.token_hash == token_hash,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now,
                User.is_active.is_(True),
            )
            .options(
                selectinload(AuthSession.user).selectinload(User.organization),
                selectinload(AuthSession.user)
                .selectinload(User.user_roles)
                .selectinload(UserRole.role),
            )
        )
        .scalars()
        .first()
    )

    if not session:
        return None

    session.last_seen_at = now
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def revoke_session(db: Session, session: AuthSession) -> None:
    session.revoked_at = utcnow()
    db.add(session)
    db.commit()


def mark_step_up(db: Session, session: AuthSession) -> AuthSession:
    session.step_up_verified_at = utcnow()
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def has_recent_step_up(session: AuthSession) -> bool:
    settings = get_settings()
    if not session.step_up_verified_at:
        return False

    step_up_verified_at = session.step_up_verified_at
    if step_up_verified_at.tzinfo is None:
        step_up_verified_at = step_up_verified_at.replace(tzinfo=UTC)
    return step_up_verified_at >= utcnow() - timedelta(minutes=settings.step_up_window_minutes)


def create_api_token(
    db: Session,
    *,
    user: User,
    label: str,
    raw_token: str,
    encryption_key: bytes,
    expires_in_days_override: int | None = None,
) -> ApiToken:
    settings = get_settings()
    ttl_days = expires_in_days_override or settings.api_token_ttl_days
    token = ApiToken(
        user_id=user.id,
        org_id=user.org_id,
        label=label,
        token_hash=hash_token(raw_token),
        token_ciphertext=encrypt_token(raw_token, encryption_key),
        expires_at=expires_in_days(ttl_days),
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def list_api_tokens(db: Session, *, user_id: str) -> list[ApiToken]:
    return list(
        db.execute(
            select(ApiToken)
            .where(ApiToken.user_id == user_id)
            .order_by(ApiToken.created_at.desc())
        )
        .scalars()
        .all()
    )


def revoke_api_token(db: Session, *, user_id: str, token_id: str) -> bool:
    token = (
        db.execute(select(ApiToken).where(ApiToken.id == token_id, ApiToken.user_id == user_id))
        .scalars()
        .first()
    )
    if not token:
        return False

    token.revoked_at = utcnow()
    db.add(token)
    db.commit()
    return True


def get_active_api_token(db: Session, raw_token: str) -> ApiToken | None:
    token_hash = hash_token(raw_token)
    now = utcnow()
    token = (
        db.execute(
            select(ApiToken)
            .join(User, ApiToken.user_id == User.id)
            .where(
                ApiToken.token_hash == token_hash,
                ApiToken.revoked_at.is_(None),
                ApiToken.expires_at > now,
                User.is_active.is_(True),
            )
            .options(
                selectinload(ApiToken.user).selectinload(User.organization),
                selectinload(ApiToken.user)
                .selectinload(User.user_roles)
                .selectinload(UserRole.role),
            )
        )
        .scalars()
        .first()
    )
    if not token:
        return None

    token.last_used_at = now
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def serialize_user(session: AuthSession) -> dict:
    step_up_valid_until = None
    if session.step_up_verified_at:
        step_up_valid_until = session.step_up_verified_at + timedelta(
            minutes=get_settings().step_up_window_minutes
        )

    return {
        "id": session.user.id,
        "username": session.user.username,
        "org_id": session.user.organization.id,
        "org_slug": session.user.organization.slug,
        "roles": _user_roles(session.user),
        "step_up_valid_until": step_up_valid_until,
    }
