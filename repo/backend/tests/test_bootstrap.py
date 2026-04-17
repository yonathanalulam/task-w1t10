from __future__ import annotations

from sqlalchemy import select

from app.core.config import clear_settings_cache
from app.models.organization import Organization
from app.models.rbac import Role, UserRole
from app.models.user import User
from app.services.auth import authenticate_user
from app.services.bootstrap import DEMO_SEED_USERS, ensure_bootstrap_state, read_bootstrap_credentials_once


def test_bootstrap_credentials_are_encrypted_at_rest(db, monkeypatch, tmp_path):
    creds_path = tmp_path / "bootstrap" / "admin_credentials.txt"
    key_path = tmp_path / "bootstrap" / "token_encryption.key"

    monkeypatch.setenv("TF_BOOTSTRAP_ADMIN_USERNAME", "pytest-bootstrap-admin")
    monkeypatch.setenv("TF_BOOTSTRAP_CREDS_PATH", str(creds_path))
    monkeypatch.setenv("TF_TOKEN_ENCRYPTION_KEY_PATH", str(key_path))
    clear_settings_cache()

    try:
        ensure_bootstrap_state(db)

        raw = creds_path.read_text(encoding="utf-8")
        assert "password=" not in raw
        assert "password_ciphertext=" in raw

        plaintext = read_bootstrap_credentials_once(path=str(creds_path))
        assert "username=pytest-bootstrap-admin" in plaintext
        assert "password=" in plaintext
        assert not creds_path.exists()
    finally:
        clear_settings_cache()


def test_demo_seed_users_provisioned_when_enabled(db, monkeypatch):
    monkeypatch.setenv("TF_DEMO_SEED_USERS", "true")
    clear_settings_cache()

    try:
        ensure_bootstrap_state(db)

        org = db.execute(select(Organization).where(Organization.slug == "default-org")).scalars().one()

        for username, role_name in DEMO_SEED_USERS.items():
            user = (
                db.execute(select(User).where(User.org_id == org.id, User.username == username))
                .scalars()
                .one()
            )
            assert user.is_active is True

            role_names = [
                db.execute(select(Role).where(Role.id == user_role.role_id)).scalars().one().name
                for user_role in db.execute(select(UserRole).where(UserRole.user_id == user.id))
                .scalars()
                .all()
            ]
            assert role_name in role_names

            authenticated = authenticate_user(db, "default-org", username, "TrailForgeDemo!123")
            assert authenticated is not None
            assert authenticated.username == username
    finally:
        clear_settings_cache()
        for username in DEMO_SEED_USERS:
            user = (
                db.execute(select(User).where(User.username == username))
                .scalars()
                .first()
            )
            if user is None:
                continue
            for user_role in db.execute(select(UserRole).where(UserRole.user_id == user.id)).scalars().all():
                db.delete(user_role)
            db.delete(user)
        db.commit()
