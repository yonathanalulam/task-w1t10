from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class ObjectStorageError(Exception):
    """Raised when object storage operations fail safely."""


@dataclass(slots=True)
class StoredObject:
    key: str
    absolute_path: Path
    size_bytes: int


class LocalDiskObjectStorage:
    def __init__(self, *, root_path: str):
        self._root = Path(root_path).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, key: str) -> Path:
        key_path = Path(key)
        if key_path.is_absolute():
            raise ObjectStorageError("Absolute storage keys are not allowed")

        candidate = (self._root / key_path).resolve()
        if self._root not in candidate.parents and candidate != self._root:
            raise ObjectStorageError("Storage key escaped configured root")
        return candidate

    def put_bytes(self, *, key: str, data: bytes) -> StoredObject:
        target = self._resolve_path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return StoredObject(key=key, absolute_path=target, size_bytes=len(data))

    def open_read(self, *, key: str):
        target = self._resolve_path(key)
        if not target.exists() or not target.is_file():
            raise ObjectStorageError("Stored file was not found")
        return target.open("rb")

    def delete(self, *, key: str, missing_ok: bool = True) -> bool:
        target = self._resolve_path(key)
        if not target.exists():
            if missing_ok:
                return False
            raise ObjectStorageError("Stored file was not found")
        if not target.is_file():
            raise ObjectStorageError("Stored object is not a file")

        target.unlink()

        parent = target.parent
        while parent != self._root and parent.exists():
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent
        return True
