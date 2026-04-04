from __future__ import annotations

import logging
import time

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import utcnow
from app.services.operations import run_asset_cleanup_cycle, run_nightly_backups_for_all_orgs, run_retention_for_all_orgs

logger = logging.getLogger("trailforge.operations_daemon")


def run_cycle() -> None:
    settings = get_settings()
    now = utcnow()
    with SessionLocal() as db:
        cleanup_marked, cleanup_deleted = run_asset_cleanup_cycle(db, max_delete=settings.asset_cleanup_batch_size)
        if cleanup_marked or cleanup_deleted:
            logger.info(
                "Asset cleanup cycle completed; marked_orphaned=%s deleted=%s",
                cleanup_marked,
                cleanup_deleted,
            )

        retention_runs = run_retention_for_all_orgs(db)
        if retention_runs:
            logger.info("Retention cycle completed; created_runs=%s", retention_runs)

        if now.hour == settings.nightly_backup_hour_utc:
            created_runs = run_nightly_backups_for_all_orgs(db)
            logger.info("Nightly backup cycle completed; created_runs=%s", created_runs)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = get_settings()
    logger.info(
        "Starting operations daemon (poll=%ss, nightly_backup_hour_utc=%s)",
        settings.operations_poll_seconds,
        settings.nightly_backup_hour_utc,
    )

    while True:
        try:
            run_cycle()
        except Exception:
            logger.exception("Operations daemon cycle failed")
        time.sleep(settings.operations_poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
