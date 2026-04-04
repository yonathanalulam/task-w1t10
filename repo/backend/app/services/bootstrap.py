from __future__ import annotations

import base64
import logging
import secrets
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_random_secret, hash_password, load_or_create_token_key
from app.models.organization import Organization
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User


logger = logging.getLogger(__name__)
BOOTSTRAP_CREDS_FORMAT = "trailforge-bootstrap-credentials-v1"


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
        "Bootstrap admin user created. Retrieve one-time credentials from %s with the bootstrap read helper",
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

    nonce = secrets.token_bytes(12)
    aad = _bootstrap_credentials_aad(org_slug, username)
    encrypted_password = AESGCM(_bootstrap_credentials_key()).encrypt(nonce, password.encode("utf-8"), aad)

    path.write_text(
        "\n".join(
            [
                "TrailForge bootstrap credentials envelope",
                f"format={BOOTSTRAP_CREDS_FORMAT}",
                f"org_slug={org_slug}",
                f"username={username}",
                f"nonce={base64.urlsafe_b64encode(nonce).decode('ascii')}",
                f"password_ciphertext={base64.urlsafe_b64encode(encrypted_password).decode('ascii')}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)


def read_bootstrap_credentials_once(*, path: str | None = None, delete_after_read: bool = True) -> str:
    creds_path = Path(path or get_settings().bootstrap_creds_path)
    raw = creds_path.read_text(encoding="utf-8")
    parsed = _parse_credentials_file(raw)

    if parsed.get("format") == BOOTSTRAP_CREDS_FORMAT:
        org_slug = parsed.get("org_slug")
        username = parsed.get("username")
        nonce = parsed.get("nonce")
        password_ciphertext = parsed.get("password_ciphertext")
        if not org_slug or not username or not nonce or not password_ciphertext:
            raise RuntimeError("Bootstrap credentials file is incomplete")

        password = AESGCM(_bootstrap_credentials_key()).decrypt(
            base64.urlsafe_b64decode(nonce.encode("ascii")),
            base64.urlsafe_b64decode(password_ciphertext.encode("ascii")),
            _bootstrap_credentials_aad(org_slug, username),
        ).decode("utf-8")
        plaintext = (
            "TrailForge bootstrap credentials\n"
            f"org_slug={org_slug}\n"
            f"username={username}\n"
            f"password={password}\n"
        )
    elif "password" in parsed:
        plaintext = raw if raw.endswith("\n") else raw + "\n"
    else:
        raise RuntimeError("Bootstrap credentials file is invalid")

    if delete_after_read:
        creds_path.unlink(missing_ok=True)
    return plaintext


def _bootstrap_credentials_key() -> bytes:
    encoded_key = load_or_create_token_key(get_settings().token_encryption_key_path)
    try:
        return base64.urlsafe_b64decode(encoded_key)
    except Exception as exc:  # pragma: no cover - defensive branch
        raise RuntimeError("Bootstrap credentials key is invalid") from exc


def _bootstrap_credentials_aad(org_slug: str, username: str) -> bytes:
    return f"{BOOTSTRAP_CREDS_FORMAT}\n{org_slug}\n{username}".encode("utf-8")


def _parse_credentials_file(raw: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in raw.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed
