from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_random_secret, hash_password
from app.models.organization import Organization
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User


logger = logging.getLogger(__name__)


ROLE_MAP: dict[str, list[str]] = {
    "ORG_ADMIN": [
        "org.manage",
        "project.manage",
        "dataset.manage",
        "itinerary.manage",
        "audit.read",
        "rbac.manage",
    ],
    "PLANNER": [
        "itinerary.read",
        "itinerary.write",
        "dataset.read",
        "message.write",
    ],
    "AUDITOR": ["audit.read", "itinerary.read", "dataset.read", "message.read"],
}


def ensure_bootstrap_state(db: Session) -> None:
    settings = get_settings()

    org = db.execute(select(Organization).where(Organization.slug == settings.bootstrap_org_slug)).scalars().first()
    if not org:
        org = Organization(slug=settings.bootstrap_org_slug, name=settings.bootstrap_org_name)
        db.add(org)
        db.commit()
        db.refresh(org)

    permissions = _ensure_permissions(db)
    roles = _ensure_roles(db, org.id)
    _ensure_role_permissions(db, roles, permissions)
    _ensure_admin_user(db, org.id, roles["ORG_ADMIN"].id)


def _ensure_permissions(db: Session) -> dict[str, Permission]:
    permission_codes = sorted({code for codes in ROLE_MAP.values() for code in codes})
    existing = {
        permission.code: permission
        for permission in db.execute(select(Permission).where(Permission.code.in_(permission_codes))).scalars().all()
    }

    for code in permission_codes:
        if code not in existing:
            permission = Permission(code=code, description=f"Permission for {code}")
            db.add(permission)
            db.commit()
            db.refresh(permission)
            existing[code] = permission

    return existing


def _ensure_roles(db: Session, org_id: str) -> dict[str, Role]:
    existing = {
        role.name: role for role in db.execute(select(Role).where(Role.org_id == org_id)).scalars().all()
    }
    for role_name in ROLE_MAP:
        if role_name not in existing:
            role = Role(org_id=org_id, name=role_name)
            db.add(role)
            db.commit()
            db.refresh(role)
            existing[role_name] = role
    return existing


def _ensure_role_permissions(
    db: Session,
    roles: dict[str, Role],
    permissions: dict[str, Permission],
) -> None:
    for role_name, permission_codes in ROLE_MAP.items():
        role = roles[role_name]
        existing_permission_ids = {
            rp.permission_id
            for rp in db.execute(select(RolePermission).where(RolePermission.role_id == role.id)).scalars().all()
        }
        for code in permission_codes:
            permission = permissions[code]
            if permission.id in existing_permission_ids:
                continue
            db.add(RolePermission(role_id=role.id, permission_id=permission.id))
        db.commit()


def _ensure_admin_user(db: Session, org_id: str, admin_role_id: str) -> None:
    settings = get_settings()
    existing_user = (
        db.execute(
            select(User).where(User.org_id == org_id, User.username == settings.bootstrap_admin_username)
        )
        .scalars()
        .first()
    )

    if existing_user:
        _ensure_user_role(db, existing_user.id, admin_role_id)
        return

    password = create_random_secret(24)
    user = User(
        org_id=org_id,
        username=settings.bootstrap_admin_username,
        password_hash=hash_password(password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    _ensure_user_role(db, user.id, admin_role_id)
    _write_credentials_file(settings.bootstrap_org_slug, settings.bootstrap_admin_username, password)
    logger.warning(
        "Bootstrap admin user created. Retrieve one-time credentials from %s",
        settings.bootstrap_creds_path,
    )


def _ensure_user_role(db: Session, user_id: str, role_id: str) -> None:
    existing = (
        db.execute(select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id))
        .scalars()
        .first()
    )
    if existing:
        return
    db.add(UserRole(user_id=user_id, role_id=role_id))
    db.commit()


def _write_credentials_file(org_slug: str, username: str, password: str) -> None:
    settings = get_settings()
    path = Path(settings.bootstrap_creds_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "TrailForge bootstrap credentials",
                f"org_slug={org_slug}",
                f"username={username}",
                f"password={password}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)
