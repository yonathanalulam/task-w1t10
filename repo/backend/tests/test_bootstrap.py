from __future__ import annotations

from app.core.config import clear_settings_cache
from app.services.bootstrap import ensure_bootstrap_state, read_bootstrap_credentials_once


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
