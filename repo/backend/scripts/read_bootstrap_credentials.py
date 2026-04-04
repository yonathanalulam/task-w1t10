from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.bootstrap import read_bootstrap_credentials_once


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        sys.stdout.write(read_bootstrap_credentials_once(path=path))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
