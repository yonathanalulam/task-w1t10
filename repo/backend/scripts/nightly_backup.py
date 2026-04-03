from __future__ import annotations

from app.core.database import SessionLocal
from app.services.operations import run_nightly_backups_for_all_orgs


def main() -> int:
    with SessionLocal() as db:
        created_count = run_nightly_backups_for_all_orgs(db)
        print(f"Nightly backup cycle complete; created_runs={created_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
