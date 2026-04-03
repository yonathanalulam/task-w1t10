from __future__ import annotations

import os
from pathlib import Path
import shutil
from collections.abc import Generator
import base64

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import delete, text
from sqlalchemy.orm import Session

TEST_ASSET_ROOT = Path("/tmp/trailforge-test-assets")
TEST_RUNTIME_ROOT = Path("/tmp/trailforge-test-runtime")
TEST_SECRET_ROOT = TEST_RUNTIME_ROOT / "secrets"
TEST_BACKUP_ROOT = TEST_RUNTIME_ROOT / "backups"
TEST_DB_PATH = TEST_RUNTIME_ROOT / "trailforge-test.db"
TEST_BOOTSTRAP_CREDS_PATH = TEST_RUNTIME_ROOT / "bootstrap" / "admin_credentials.txt"
TEST_TOKEN_KEY_PATH = TEST_RUNTIME_ROOT / "bootstrap" / "token_encryption.key"
TEST_BACKUP_KEY_PATH = TEST_SECRET_ROOT / "backup_encryption_key"

TEST_RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
TEST_SECRET_ROOT.mkdir(parents=True, exist_ok=True)
TEST_BACKUP_ROOT.mkdir(parents=True, exist_ok=True)

if not TEST_BACKUP_KEY_PATH.exists() or not TEST_BACKUP_KEY_PATH.read_bytes().strip():
    key = base64.urlsafe_b64encode(os.urandom(32))
    TEST_BACKUP_KEY_PATH.write_bytes(key)
TEST_BACKUP_KEY_PATH.chmod(0o600)

if not os.environ.get("DATABASE_URL") and not os.environ.get("TF_DATABASE_URL") and not os.environ.get("TF_DB_HOST"):
    sqlite_url = f"sqlite+pysqlite:///{TEST_DB_PATH}"
    os.environ["DATABASE_URL"] = sqlite_url
    os.environ["TF_DATABASE_URL"] = sqlite_url

os.environ.setdefault("TF_ASSET_STORAGE_ROOT", str(TEST_ASSET_ROOT))
os.environ.setdefault("TF_BACKUP_ROOT", str(TEST_BACKUP_ROOT))
os.environ.setdefault("TF_BACKUP_ENCRYPTION_KEY_PATH", str(TEST_BACKUP_KEY_PATH))
os.environ.setdefault("TF_BOOTSTRAP_CREDS_PATH", str(TEST_BOOTSTRAP_CREDS_PATH))
os.environ.setdefault("TF_TOKEN_ENCRYPTION_KEY_PATH", str(TEST_TOKEN_KEY_PATH))

from app.core.config import clear_settings_cache, get_settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.main import app
from app.models.auth import ApiToken, Session as AuthSession
from app.models.governance import Attraction, AttractionMergeEvent, Dataset, Project, ProjectDataset, ProjectMember
from app.models.message_center import MessageDeliveryAttempt, MessageDispatch, MessageTemplate
from app.models.operations import AuditEvent, BackupRun, LineageEvent, RestoreRun, RetentionPolicy, RetentionRun
from app.models.organization import Organization
from app.models.planner import Itinerary, ItineraryDay, ItineraryStop, ItineraryVersion
from app.models.rbac import Role, UserRole
from app.models.user import User
from app.services.bootstrap import ensure_bootstrap_state


@pytest.fixture(scope="session", autouse=True)
def test_settings() -> Generator[None, None, None]:
    os.environ["TF_SESSION_COOKIE_SECURE"] = "false"
    clear_settings_cache()

    settings = get_settings()
    if settings.resolved_database_url().startswith("sqlite"):
        TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        alembic_cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        command.upgrade(alembic_cfg, "head")

    yield


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        ensure_bootstrap_state(session)
        yield session


@pytest.fixture(autouse=True)
def clean_test_users(db: Session) -> Generator[None, None, None]:
    yield
    db.rollback()
    db.execute(delete(ApiToken).where(ApiToken.label.like("pytest-%")))
    db.execute(delete(AuthSession))
    db.execute(delete(MessageDeliveryAttempt))
    db.execute(delete(MessageDispatch))
    db.execute(delete(MessageTemplate).where(MessageTemplate.name.like("pytest-%")))
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("TRUNCATE TABLE audit_events, lineage_events RESTART IDENTITY CASCADE"))
    else:
        db.execute(text("DROP TRIGGER IF EXISTS trg_audit_events_immutable_update"))
        db.execute(text("DROP TRIGGER IF EXISTS trg_audit_events_immutable_delete"))
        db.execute(text("DROP TRIGGER IF EXISTS trg_lineage_events_immutable_update"))
        db.execute(text("DROP TRIGGER IF EXISTS trg_lineage_events_immutable_delete"))
        db.execute(delete(AuditEvent))
        db.execute(delete(LineageEvent))
        db.execute(
            text(
                """
                CREATE TRIGGER trg_audit_events_immutable_update
                BEFORE UPDATE ON audit_events
                BEGIN
                    SELECT RAISE(FAIL, 'Immutable table audit_events cannot be UPDATE');
                END;
                """
            )
        )
        db.execute(
            text(
                """
                CREATE TRIGGER trg_audit_events_immutable_delete
                BEFORE DELETE ON audit_events
                BEGIN
                    SELECT RAISE(FAIL, 'Immutable table audit_events cannot be DELETE');
                END;
                """
            )
        )
        db.execute(
            text(
                """
                CREATE TRIGGER trg_lineage_events_immutable_update
                BEFORE UPDATE ON lineage_events
                BEGIN
                    SELECT RAISE(FAIL, 'Immutable table lineage_events cannot be UPDATE');
                END;
                """
            )
        )
        db.execute(
            text(
                """
                CREATE TRIGGER trg_lineage_events_immutable_delete
                BEFORE DELETE ON lineage_events
                BEGIN
                    SELECT RAISE(FAIL, 'Immutable table lineage_events cannot be DELETE');
                END;
                """
            )
        )
    db.execute(delete(RestoreRun))
    db.execute(delete(BackupRun))
    db.execute(delete(RetentionRun))
    db.execute(delete(RetentionPolicy))
    db.execute(delete(ItineraryVersion))
    db.execute(delete(ItineraryStop))
    db.execute(delete(ItineraryDay))
    db.execute(delete(Itinerary).where(Itinerary.name.like("pytest-%")))
    db.execute(delete(AttractionMergeEvent))
    db.execute(delete(Attraction).where(Attraction.name.like("pytest-%")))
    db.execute(delete(ProjectDataset))
    db.execute(delete(ProjectMember))
    db.execute(delete(Project).where(Project.name.like("pytest-%")))
    db.execute(delete(Dataset).where(Dataset.name.like("pytest-%")))
    db.execute(delete(UserRole))
    db.execute(delete(User).where(User.username.like("pytest-%")))
    db.execute(delete(Role).where(Role.name.like("PYTEST_%")))
    db.execute(delete(Organization).where(Organization.slug.like("pytest-%")))
    db.commit()
    shutil.rmtree(TEST_ASSET_ROOT, ignore_errors=True)


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


def _create_user(db: Session, *, org: Organization, username: str, password: str, role_name: str) -> User:
    role = db.query(Role).filter_by(org_id=org.id, name=role_name).one()
    user = User(
        org_id=org.id,
        username=username,
        password_hash=hash_password(password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    return user


@pytest.fixture()
def test_user(db: Session) -> dict[str, str]:
    org = db.query(Organization).filter_by(slug="default-org").one()
    user = _create_user(
        db,
        org=org,
        username="pytest-admin",
        password="pytest-pass-123",
        role_name="ORG_ADMIN",
    )

    return {
        "org_slug": "default-org",
        "username": "pytest-admin",
        "password": "pytest-pass-123",
        "user_id": user.id,
    }


@pytest.fixture()
def planner_user(db: Session) -> dict[str, str]:
    org = db.query(Organization).filter_by(slug="default-org").one()
    user = _create_user(
        db,
        org=org,
        username="pytest-planner",
        password="pytest-pass-123",
        role_name="PLANNER",
    )
    return {
        "org_slug": "default-org",
        "username": "pytest-planner",
        "password": "pytest-pass-123",
        "user_id": user.id,
    }


@pytest.fixture()
def auditor_user(db: Session) -> dict[str, str]:
    org = db.query(Organization).filter_by(slug="default-org").one()
    user = _create_user(
        db,
        org=org,
        username="pytest-auditor",
        password="pytest-pass-123",
        role_name="AUDITOR",
    )
    return {
        "org_slug": "default-org",
        "username": "pytest-auditor",
        "password": "pytest-pass-123",
        "user_id": user.id,
    }


@pytest.fixture()
def other_org_admin(db: Session) -> dict[str, str]:
    org = Organization(slug="pytest-org-2", name="Pytest Org 2")
    db.add(org)
    db.commit()
    db.refresh(org)

    for role_name in ("ORG_ADMIN", "PLANNER", "AUDITOR"):
        db.add(Role(org_id=org.id, name=role_name))
    db.commit()

    user = _create_user(
        db,
        org=org,
        username="pytest-admin-2",
        password="pytest-pass-123",
        role_name="ORG_ADMIN",
    )
    return {
        "org_slug": "pytest-org-2",
        "username": "pytest-admin-2",
        "password": "pytest-pass-123",
        "user_id": user.id,
    }
