#!/bin/bash
set -euo pipefail
mkdir -p program/repros repo/src repo/tests

if [ -n "${ASTACK_EVAL_SETTINGS_JSON:-}" ]; then
  printf '%s\n' "$ASTACK_EVAL_SETTINGS_JSON" > program/settings.json
else
cat > program/settings.json <<'EOF'
{
  "worker_minutes": 60,
  "reviewer_minutes": 30,
  "researcher_minutes": 30,
  "wind_down_minutes": 5,
  "check_in_minutes": 5,
  "roles": {
    "worker": {"provider": "anthropic", "model": "haiku", "effort": "medium"}
  },
  "reviewer_pool": [
    {"provider": "anthropic", "model": "sonnet", "effort": "medium"},
    {"provider": "anthropic", "model": "haiku", "effort": "medium"}
  ]
}
EOF
fi

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/vault.py <<'EOF'
from __future__ import annotations

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
        sig = hmac.new(self._secret, tenant.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{tenant}:{sig}"

    def authenticate(self, token: str) -> str:
        # BUG 1 (fail-open): malformed token without ':' falls back to guest instead of denying
        if ":" not in token:
            return "guest"
        tenant, sig = token.split(":", 1)
        expected = hmac.new(self._secret, tenant.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise PermissionError("invalid token")
        return tenant

    def _check_quota(self, tenant: str) -> None:
        with self._lock:
            if self._counts.get(tenant, 0) >= self._max_writes:
                raise RuntimeError("quota exceeded")

    def _inc_quota(self, tenant: str) -> None:
        with self._lock:
            self._counts[tenant] = self._counts.get(tenant, 0) + 1

    def write_blob(self, token: str, name: str, data: bytes) -> Path:
        tenant = self.authenticate(token)
        # BUG 2 (split-lock race): check and increment release lock in between
        self._check_quota(tenant)
        # BUG 3 (path traversal): unsanitized name escapes tenant directory
        target = self.root / tenant / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        self._inc_quota(tenant)
        return target
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_vault.py <<'EOF'
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from vault import TenantVault


class TenantVaultTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="vault-test-"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def test_valid_tenant_write_succeeds(self):
        v = TenantVault(self.dir, b"secret", max_writes=2)
        tok = v.make_token("acme")
        p = v.write_blob(tok, "hello.txt", b"ok")
        self.assertEqual(p.read_bytes(), b"ok")


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial tenant vault service"
git -C repo rev-parse HEAD > program/main_sha.txt
