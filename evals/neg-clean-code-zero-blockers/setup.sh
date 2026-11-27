#!/bin/bash
set -euo pipefail
mkdir -p repo/src repo/tests program

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# Atomic Store

Durable thread-safe JSON key-value store backed by atomic temp-file writes (`os.fsync` + `os.replace`).
EOF

git -C repo add README.md
git -C repo commit -q -m "initial"

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/atomic_store.py <<'EOF'
from __future__ import annotations

import copy
import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any


def _validate_key(key: str) -> str:
    if not isinstance(key, str) or not key or not key.strip():
        raise ValueError("key must be a non-empty string")
    if "\x00" in key:
        raise ValueError("key must not contain NUL bytes")
    return key


def _validate_json_value(value: Any) -> Any:
    try:
        encoded = json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"value is not valid JSON: {exc}") from exc
    return json.loads(encoded)


class AtomicKVStore:
    """Thread-safe JSON key-value store persisted via temp file + fsync + os.replace."""

    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path):
            raise TypeError("path must be a pathlib.Path")
        if path.exists() and path.is_dir():
            raise ValueError(f"store path must be a file, not a directory: {path}")
        self._path = path
        self._lock = threading.Lock()

    def _read_unlocked(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        raw = self._path.read_text(encoding="utf-8")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"corrupt store JSON in {self._path}: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ValueError(f"store root in {self._path} must be a JSON object")
        return parsed

    def _write_unlocked(self, data: dict[str, Any]) -> None:
        parent = self._path.parent
        parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(data, sort_keys=True, indent=2, allow_nan=False) + "\n"
        tmp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=parent,
                prefix=f".{self._path.name}.",
                suffix=".tmp",
                delete=False,
            ) as tmp_file:
                tmp_path = Path(tmp_file.name)
                tmp_file.write(payload)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())
            os.replace(tmp_path, self._path)
            tmp_path = None
        finally:
            if tmp_path is not None:
                try:
                    tmp_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def get(self, key: str, default: Any = None) -> Any:
        valid_key = _validate_key(key)
        with self._lock:
            data = self._read_unlocked()
            if valid_key not in data:
                return default
            return copy.deepcopy(data[valid_key])

    def set(self, key: str, value: Any) -> None:
        valid_key = _validate_key(key)
        clean_value = _validate_json_value(value)
        with self._lock:
            data = self._read_unlocked()
            data[valid_key] = clean_value
            self._write_unlocked(data)

    def delete(self, key: str) -> bool:
        valid_key = _validate_key(key)
        with self._lock:
            data = self._read_unlocked()
            if valid_key not in data:
                return False
            del data[valid_key]
            self._write_unlocked(data)
            return True

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._read_unlocked())
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_atomic_store.py <<'EOF'
import shutil
import tempfile
import threading
import unittest
from pathlib import Path

from src.atomic_store import AtomicKVStore


class AtomicKVStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="atomic-store-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.store_path = self.tmp / "kv.json"

    def test_set_get_delete_and_reload(self):
        store = AtomicKVStore(self.store_path)
        self.assertIsNone(store.get("missing"))
        store.set("user:1", {"role": "editor", "count": 3})
        fetched = store.get("user:1")
        self.assertEqual(fetched, {"role": "editor", "count": 3})
        fetched["role"] = "tampered"
        self.assertEqual(store.get("user:1")["role"], "editor")

        reloaded = AtomicKVStore(self.store_path)
        self.assertEqual(reloaded.snapshot(), {"user:1": {"role": "editor", "count": 3}})
        self.assertTrue(reloaded.delete("user:1"))
        self.assertFalse(reloaded.delete("user:1"))
        self.assertIsNone(reloaded.get("user:1"))

    def test_boundary_validation(self):
        with self.assertRaises(ValueError):
            AtomicKVStore(self.tmp)
        store = AtomicKVStore(self.store_path)
        for bad_key in ("", "   ", "bad\x00key"):
            with self.assertRaises(ValueError):
                store.set(bad_key, 1)
        with self.assertRaises(ValueError):
            store.set("nan", float("nan"))
        self.store_path.write_text("{corrupt", encoding="utf-8")
        with self.assertRaises(ValueError):
            store.get("a")

    def test_concurrent_updates_preserve_all_keys(self):
        store = AtomicKVStore(self.store_path)
        barrier = threading.Barrier(8)
        errors: list[Exception] = []

        def worker(idx: int) -> None:
            try:
                barrier.wait()
                for j in range(5):
                    store.set(f"t{idx}-k{j}", idx * 10 + j)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])
        snap = store.snapshot()
        self.assertEqual(len(snap), 40)
        leftover_tmp = list(self.tmp.glob("*.tmp"))
        self.assertEqual(leftover_tmp, [])


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add -A
git -C repo commit -q -m "feat: add thread-safe AtomicKVStore with fsync and atomic replace"
git -C repo diff HEAD~1..HEAD > program/change.diff
