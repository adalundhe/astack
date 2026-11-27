"""Separated offline oracle for `bugbash-investigates-and-proves-fix`."""
from __future__ import annotations

import subprocess
from pathlib import Path

_FIXED_LEDGER = '''from __future__ import annotations

from typing import Any, Callable

from cache import ResultCache


class TransferLedger:
    """Executes idempotent transfers through a settlement gateway."""

    def __init__(self, gateway: Callable[[str, int], str], cache: ResultCache | None = None) -> None:
        self._gateway = gateway
        self._cache = cache or ResultCache()

    def submit(self, tenant_id: str, idempotency_key: str, amount_cents: int) -> dict[str, Any]:
        cache_key = (tenant_id, idempotency_key)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return dict(cached)

        try:
            tx_id = self._gateway(tenant_id, amount_cents)
        except RuntimeError as exc:
            return {"status": "error", "tenant_id": tenant_id, "error": str(exc)}

        result = {
            "status": "ok",
            "tenant_id": tenant_id,
            "tx_id": tx_id,
            "amount_cents": amount_cents,
        }
        self._cache.set(cache_key, result)
        return dict(result)
'''

_FIXED_TESTS = '''import sys
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

    def test_transient_gateway_error_is_not_cached_and_retry_succeeds(self):
        attempts = {"count": 0}

        def flaky_gateway(tenant_id, amount_cents):
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise RuntimeError("gateway timeout")
            return f"tx-{tenant_id}-{attempts['count']}"

        ledger = TransferLedger(flaky_gateway)
        first = ledger.submit("tenant-a", "order-42", 2500)
        second = ledger.submit("tenant-a", "order-42", 2500)
        third = ledger.submit("tenant-a", "order-42", 2500)

        self.assertEqual(first["status"], "error")
        self.assertEqual(second["status"], "ok")
        self.assertEqual(third, second)
        self.assertEqual(attempts["count"], 2)

    def test_distinct_tenants_sharing_idempotency_key_are_isolated(self):
        calls = []

        def gateway(tenant_id, amount_cents):
            calls.append((tenant_id, amount_cents))
            return f"tx-{tenant_id}-{len(calls)}"

        ledger = TransferLedger(gateway)
        tenant_a = ledger.submit("tenant-a", "req-1", 1000)
        tenant_b = ledger.submit("tenant-b", "req-1", 2000)
        tenant_a_replay = ledger.submit("tenant-a", "req-1", 1000)

        self.assertEqual(tenant_a["tenant_id"], "tenant-a")
        self.assertEqual(tenant_b["tenant_id"], "tenant-b")
        self.assertNotEqual(tenant_a["tx_id"], tenant_b["tx_id"])
        self.assertEqual(tenant_a_replay, tenant_a)
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
'''

_PR_BODY = """# Fix TransferLedger idempotency cache scoping and transient error caching

## Root Causes
1. `TransferLedger.submit` in `src/ledger.py` cached results under `idempotency_key` alone instead of `(tenant_id, idempotency_key)`, causing `tenant-b` to receive `tenant-a`'s receipt when reusing the same key.
2. `TransferLedger.submit` wrote `status == "error"` results into `ResultCache` after a `RuntimeError` from the gateway, so subsequent retries never reached the gateway after recovery.

## Fix
- Key `ResultCache` entries by `(tenant_id, idempotency_key)` in `src/ledger.py`.
- Return transient error dicts immediately without caching them; cache only terminal `status == "ok"` results.
- Added red-first regression tests in `tests/test_ledger.py` covering retry recovery after transient errors and cross-tenant isolation.

## Verification
- Before fix: both new regression tests fail against `main` (`src/ledger.py` replays stale `status == "error"` and leaks `tenant-a`'s receipt to `tenant-b`).
- After fix: `python3 -m unittest discover -s tests` passes all 3 tests, confirming transient errors retry, distinct tenants stay isolated, and repeated same-tenant successes replay without double-charging.
"""


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


def apply(ws: Path) -> dict[str, object]:
    repo = ws / "repo"
    _git(repo, "checkout", "-q", "-b", "fix/transfer-ledger-idempotency")
    (repo / "src" / "ledger.py").write_text(_FIXED_LEDGER, encoding="utf-8")
    (repo / "tests" / "test_ledger.py").write_text(_FIXED_TESTS, encoding="utf-8")
    _git(repo, "add", "src/ledger.py", "tests/test_ledger.py")
    _git(repo, "commit", "-q", "-m", "fix: scope transfer cache by tenant and stop caching transient errors")
    (ws / "program" / "pr-body.md").write_text(_PR_BODY, encoding="utf-8")
    return {
        "final_text": (
            "Confirmed both root causes in `repo/src/ledger.py`: cache entries were keyed only by "
            "`idempotency_key` (leaking receipts across tenants) and transient gateway errors were cached "
            "indefinitely. Fixed both on branch `fix/transfer-ledger-idempotency`, added red-first regression "
            "tests in `repo/tests/test_ledger.py`, verified all tests pass, and wrote `program/pr-body.md`."
        ),
        "events": [],
    }
