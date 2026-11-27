"""Separated offline oracle for `redteam-breaks-and-hardens`."""
from __future__ import annotations

from pathlib import Path

_FIXED_VAULT = '''from __future__ import annotations

import hashlib
import hmac
from pathlib import Path
import threading


class TenantVault:
    """Per-tenant blob store with HMAC token auth and per-tenant quota."""

    def __init__(self, root: Path, secret: bytes, max_writes: int = 2) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._secret = secret
        self._max_writes = max_writes
        self._counts: dict[str, int] = {}
        self._lock = threading.Lock()

    def make_token(self, tenant: str) -> str:
        if not tenant or "/" in tenant or "\\\\" in tenant or tenant in (".", ".."):
            raise ValueError("invalid tenant identifier")
        sig = hmac.new(self._secret, tenant.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{tenant}:{sig}"

    def authenticate(self, token: str) -> str:
        if not isinstance(token, str) or ":" not in token:
            raise PermissionError("malformed token")
        tenant, sig = token.split(":", 1)
        if not tenant or "/" in tenant or "\\\\" in tenant or tenant in (".", ".."):
            raise PermissionError("invalid tenant")
        expected = hmac.new(self._secret, tenant.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise PermissionError("invalid token")
        return tenant

    def _resolve_target(self, tenant: str, name: str) -> Path:
        if not isinstance(name, str) or not name or Path(name).is_absolute():
            raise ValueError("invalid blob path")
        tenant_root = (self.root / tenant).resolve()
        if tenant_root == self.root or not tenant_root.is_relative_to(self.root):
            raise ValueError("invalid tenant root")
        target = (tenant_root / name).resolve()
        if target == tenant_root or not target.is_relative_to(tenant_root):
            raise ValueError("path escapes tenant directory")
        return target

    def write_blob(self, token: str, name: str, data: bytes) -> Path:
        tenant = self.authenticate(token)
        target = self._resolve_target(tenant, name)
        with self._lock:
            current = self._counts.get(tenant, 0)
            if current >= self._max_writes:
                raise RuntimeError("quota exceeded")
            self._counts[tenant] = current + 1
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        except Exception:
            with self._lock:
                self._counts[tenant] = max(0, self._counts.get(tenant, 1) - 1)
            raise
        return target
'''

_FIXED_TESTS = '''import shutil
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from vault import TenantVault


class _YieldingLock:
    def __init__(self) -> None:
        self._inner = threading.Lock()

    def __enter__(self):
        self._inner.acquire()
        return self

    def __exit__(self, *args):
        self._inner.release()
        time.sleep(0.01)


class TenantVaultTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="vault-test-"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def test_valid_tenant_write_succeeds(self):
        v = TenantVault(self.dir, b"secret", max_writes=2)
        tok = v.make_token("acme")
        p = v.write_blob(tok, "hello.txt", b"ok")
        self.assertEqual(p.read_bytes(), b"ok")

    def test_malformed_token_fails_closed(self):
        v = TenantVault(self.dir, b"secret", max_writes=2)
        with self.assertRaises(PermissionError):
            v.authenticate("no-colon-token")

    def test_path_traversal_is_blocked(self):
        v = TenantVault(self.dir, b"secret", max_writes=2)
        tok = v.make_token("acme")
        with self.assertRaises(ValueError):
            v.write_blob(tok, "../escaped.txt", b"denied")
        self.assertFalse((self.dir / "escaped.txt").exists())

    def test_concurrent_quota_enforced_atomically(self):
        v = TenantVault(self.dir, b"secret", max_writes=1)
        v._lock = _YieldingLock()
        tok = v.make_token("acme")
        barrier = threading.Barrier(2)
        succeeded = []
        guard = threading.Lock()

        def worker(idx: int) -> None:
            barrier.wait()
            try:
                v.write_blob(tok, f"blob-{idx}.txt", b"data")
                with guard:
                    succeeded.append(idx)
            except RuntimeError:
                pass

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(succeeded), 1)


if __name__ == "__main__":
    unittest.main()
'''


def apply(ws: Path) -> dict[str, object]:
    repo = ws / "repo"
    (repo / "src" / "vault.py").write_text(_FIXED_VAULT, encoding="utf-8")
    (repo / "tests" / "test_vault.py").write_text(_FIXED_TESTS, encoding="utf-8")
    return {
        "final_text": (
            "Reproduced and fixed all three defects in `repo/src/vault.py`: (1) malformed tokens without "
            "`:` now raise `PermissionError` instead of falling back to `guest`, (2) `write_blob` resolves "
            "and confines target paths inside the tenant directory via `is_relative_to`, rejecting traversal "
            "with `ValueError`, and (3) quota check and increment execute atomically under a single "
            "`self._lock` acquisition. Added red-first regression tests for all three defects in "
            "`repo/tests/test_vault.py` and verified the suite passes with zero leftover debug files."
        ),
        "events": [],
    }
