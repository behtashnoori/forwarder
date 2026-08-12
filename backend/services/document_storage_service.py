"""Private filesystem storage for case documents."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile
from uuid import uuid4

from flask import current_app

from backend.quarantine import QuarantinedResource, assert_instance_current


class DocumentStorageError(Exception):
    pass


def validate_storage_root(configured: str | Path | None, *, production: bool, repository_root: str | Path) -> Path:
    if not configured:
        raise RuntimeError("DOCUMENT_STORAGE_ROOT is required" + (" in Production" if production else ""))
    candidate = Path(configured).expanduser()
    if production and not candidate.is_absolute():
        raise RuntimeError("DOCUMENT_STORAGE_ROOT must be absolute in Production")
    root = candidate.resolve()
    repository = Path(repository_root).resolve()
    if production and (root == repository or repository in root.parents):
        raise RuntimeError("DOCUMENT_STORAGE_ROOT must be outside the repository/release tree in Production")
    try:
        root.mkdir(parents=True, exist_ok=True)
        if not root.is_dir():
            raise OSError("not a directory")
        with tempfile.NamedTemporaryFile(dir=root, prefix=".storage-check-", delete=True):
            pass
    except OSError as exc:
        raise RuntimeError("DOCUMENT_STORAGE_ROOT must be a writable directory") from exc
    return root


class PrivateDocumentStorage:
    def __init__(self, root: str | Path | None = None):
        configured = root or current_app.config["DOCUMENT_STORAGE_ROOT"]
        self.root = Path(configured).resolve()

    def write(self, case_id: int, extension: str, stream, maximum: int) -> tuple[str, int, str]:
        partition = Path(str(case_id)) / uuid4().hex[:2]
        # Both components are generated internally.  Resolving the child before
        # it exists is unnecessary and races on Windows when independent uploads
        # create sibling partitions concurrently.
        if partition.is_absolute() or ".." in partition.parts:
            raise DocumentStorageError("Invalid storage destination")
        directory = self.root / partition
        directory.mkdir(parents=True, exist_ok=True)
        name = f"{uuid4().hex}.{extension}"
        final_path = directory / name
        temporary = directory / f".{name}.{uuid4().hex}.tmp"
        digest = hashlib.sha256()
        size = 0
        try:
            with temporary.open("xb") as target:
                while True:
                    chunk = stream.read(64 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > maximum:
                        raise DocumentStorageError("File is larger than the configured limit")
                    digest.update(chunk)
                    target.write(chunk)
                target.flush()
                os.fsync(target.fileno())
            if size == 0:
                raise DocumentStorageError("File is empty")
            os.replace(temporary, final_path)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        return (partition / name).as_posix(), size, digest.hexdigest()

    def _resolve_key(self, storage_key: str) -> Path:
        candidate = (self.root / storage_key).resolve()
        if self.root not in candidate.parents:
            raise DocumentStorageError("Invalid storage key")
        return candidate

    def resolve_for_download(self, document, *, case) -> Path:
        """Resolve storage only after canonical owner and file revalidation."""
        assert_instance_current(case, purpose="document-download")
        assert_instance_current(document, purpose="document-download")
        if (
            document.shipment_request_id != case.id
            or document.status == "deleted"
            or not document.storage_key
        ):
            raise QuarantinedResource("resource not found")
        parts = Path(document.storage_key).parts
        if not parts or parts[0] != str(case.id):
            raise QuarantinedResource("resource not found")
        return self._resolve_key(document.storage_key)

    def remove_after_failed_transaction(self, storage_key: str | None) -> None:
        if storage_key:
            self._resolve_key(storage_key).unlink(missing_ok=True)
