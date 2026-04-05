from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TF_", extra="ignore")

    app_name: str = "TrailForge API"
    app_env: str = "local"
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    db_host: str = "postgres"
    db_port: int = 5432
    db_name: str = "trailforge"
    db_user: str = "trailforge"
    db_password_file: str = "/run/secrets/postgres_password"

    allowed_origins: list[str] = Field(
        default_factory=lambda: ["https://localhost:5173", "https://frontend:5173"]
    )

    session_cookie_name: str = "trailforge_session"
    csrf_cookie_name: str = "trailforge_csrf"
    csrf_header_name: str = "X-CSRF-Token"
    TF_SESSION_COOKIE_SECURE: bool = Field(default=True, validation_alias="TF_SESSION_COOKIE_SECURE")
    session_ttl_hours: int = 12
    step_up_window_minutes: int = 10
    api_token_ttl_days: int = 30

    bootstrap_org_slug: str = "default-org"
    bootstrap_org_name: str = "Default Organization"
    bootstrap_admin_username: str = "admin"
    bootstrap_creds_path: str = "/bootstrap/admin_credentials.txt"
    token_encryption_key_path: str = "/bootstrap/token_encryption.key"
    asset_storage_root: str = "/var/lib/trailforge/assets"
    asset_upload_max_bytes: int = 20 * 1024 * 1024
    planner_import_upload_max_bytes: int = 5 * 1024 * 1024
    planner_import_archive_max_entries: int = 200
    planner_import_archive_max_uncompressed_bytes: int = 25 * 1024 * 1024
    planner_sync_package_upload_max_bytes: int = 5 * 1024 * 1024
    planner_sync_package_max_entries: int = 64
    planner_sync_package_max_uncompressed_bytes: int = 25 * 1024 * 1024
    asset_cleanup_grace_days: int = 30
    itinerary_retention_default_days: int = 365 * 3
    audit_retention_days: int = Field(default=365, ge=365, le=365)
    lineage_retention_days: int = Field(default=365, ge=365, le=365)
    backup_root: str = "/var/lib/trailforge/backups"
    backup_rotation_days: int = 14
    backup_encryption_key_path: str = "/run/secrets/backup_encryption_key"
    nightly_backup_hour_utc: int = Field(default=2, ge=0, le=23)
    operations_poll_seconds: int = Field(default=300, ge=30, le=3600)
    asset_cleanup_batch_size: int = Field(default=200, ge=1, le=2000)

    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        password_path = Path(self.db_password_file)
        if not password_path.exists():
            raise RuntimeError(
                "Database password file is missing. Provide DATABASE_URL or TF_DB_PASSWORD_FILE at runtime."
            )

        password = password_path.read_text(encoding="utf-8").strip()
        if not password:
            raise RuntimeError("Database password file is empty.")

        quoted_user = quote_plus(self.db_user)
        quoted_password = quote_plus(password)
        return (
            f"postgresql+psycopg://{quoted_user}:{quoted_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()


def settings_for_log() -> dict[str, Any]:
    settings = get_settings()
    return {
        "app_env": settings.app_env,
        "session_cookie_secure": settings.TF_SESSION_COOKIE_SECURE,
        "allowed_origins": settings.allowed_origins,
        "csrf_cookie_name": settings.csrf_cookie_name,
        "db_host": settings.db_host,
        "db_name": settings.db_name,
    }
