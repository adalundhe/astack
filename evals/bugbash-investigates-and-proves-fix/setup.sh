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

cat > repo/README.md <<'EOF'
# Transfer Ledger Service

Executes idempotent account transfers backed by an upstream settlement gateway.
EOF

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/cache.py <<'EOF'
from __future__ import annotations

from typing import Any


class ResultCache:
    """In-memory idempotency cache."""

    def __init__(self) -> None:
        self._store: dict[Any, dict[str, Any]] = {}

    def get(self, key: Any) -> dict[str, Any] | None:
        return self._store.get(key)

    def set(self, key: Any, value: dict[str, Any]) -> None:
        self._store[key] = value
EOF

cat > repo/src/ledger.py <<'EOF'
from __future__ import annotations

from typing import Any, Callable

from cache import ResultCache


class TransferLedger:
    """Executes idempotent transfers through a settlement gateway."""

    def __init__(self, gateway: Callable[[str, int], str], cache: ResultCache | None = None) -> None:
        self._gateway = gateway
        self._cache = cache or ResultCache()

    def submit(self, tenant_id: str, idempotency_key: str, amount_cents: int) -> dict[str, Any]:
        cached = self._cache.get(idempotency_key)
        if cached is not None:
            return dict(cached)

        try:
            tx_id = self._gateway(tenant_id, amount_cents)
            result = {"status": "ok", "tenant_id": tenant_id, "tx_id": tx_id, "amount_cents": amount_cents}
        except RuntimeError as exc:
            result = {"status": "error", "tenant_id": tenant_id, "error": str(exc)}

        self._cache.set(idempotency_key, result)
        return dict(result)
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_ledger.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ledger import TransferLedger


class TransferLedgerTest(unittest.TestCase):
    def test_duplicate_request_returns_cached_success_without_double_charge(self):
        calls = []

        def gateway(tenant_id, amount_cents):
            calls.append((tenant_id, amount_cents))
            return f"tx-{len(calls)}"

        ledger = TransferLedger(gateway)
        first = ledger.submit("tenant-a", "req-1", 5000)
        second = ledger.submit("tenant-a", "req-1", 5000)
        self.assertEqual(first, second)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial transfer ledger service"
git -C repo rev-parse HEAD > program/main_sha.txt

cat > program/bug-report.md <<'EOF'
# Bug Report #118: Retried transfers stay permanently failed and return wrong tenant receipts

## Symptoms
1. After a brief upstream gateway outage, customer `tenant-a` retried `submit("tenant-a", "order-42", 2500)` once the gateway recovered, and continued receiving `{"status": "error", ...}` forever.
2. Separately, `tenant-b` submitted a new transfer with `idempotency_key="req-1"` and received `tenant-a`'s receipt instead of executing its own transfer.

## Linked Context
- Idempotency specification: `program/linked-spec.md`
- Incident trace: `program/incident-trace.log`
EOF

cat > program/linked-spec.md <<'EOF'
# Spec: Transfer Idempotency Guarantees

1. **Tenant isolation:** Idempotency keys are scoped strictly to `(tenant_id, idempotency_key)`. Two distinct tenants using the same `idempotency_key` MUST NOT share or overwrite each other's cached results.
2. **Cache only terminal successes:** Only `status == "ok"` results may be cached for replay. Transient errors (`status == "error"`) MUST NOT be cached so client retries execute once the gateway recovers.
3. **No double charges:** Repeating the same `(tenant_id, idempotency_key)` after a successful transfer MUST return the original `ok` receipt without calling the gateway again.
EOF

cat > program/incident-trace.log <<'EOF'
2026-11-24T18:01:02Z tenant=tenant-a key=order-42 gateway=ERROR("gateway timeout") -> returned status=error
2026-11-24T18:01:05Z tenant=tenant-a key=order-42 gateway=NOT_CALLED (cache hit!) -> returned stale status=error
2026-11-24T18:02:10Z tenant=tenant-a key=req-1 gateway=OK("tx-1") -> returned status=ok tenant_id=tenant-a
2026-11-24T18:02:11Z tenant=tenant-b key=req-1 gateway=NOT_CALLED (cache hit!) -> returned status=ok tenant_id=tenant-a (WRONG TENANT)
EOF
