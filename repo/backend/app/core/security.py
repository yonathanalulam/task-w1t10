from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from argon2 import PasswordHasher
from cryptography.fernet import Fernet


password_hasher = PasswordHasher()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except Exception:
        return False


def create_random_secret(size: int = 48) -> str:
    return secrets.token_urlsafe(size)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def load_or_create_token_key(key_path: str) -> bytes:
    path = Path(key_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        return path.read_bytes().strip()

    key = Fernet.generate_key()
    path.write_bytes(key)
    path.chmod(0o600)
    return key


def encrypt_token(raw_token: str, key: bytes) -> str:
    f = Fernet(key)
    encrypted = f.encrypt(raw_token.encode("utf-8"))
    return base64.urlsafe_b64encode(encrypted).decode("utf-8")


def decrypt_token(encrypted_token: str, key: bytes) -> str:
    f = Fernet(key)
    raw = base64.urlsafe_b64decode(encrypted_token.encode("utf-8"))
    return f.decrypt(raw).decode("utf-8")


def expires_in_hours(hours: int) -> datetime:
    return utcnow() + timedelta(hours=hours)


def expires_in_days(days: int) -> datetime:
    return utcnow() + timedelta(days=days)
