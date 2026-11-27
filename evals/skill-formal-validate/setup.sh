#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval User"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/lease.py <<'EOF'
"""Distributed lease state machine with fencing tokens."""
from __future__ import annotations

from enum import Enum


class LeaseState(str, Enum):
    IDLE = "IDLE"
    HELD = "HELD"
    EXPIRED = "EXPIRED"


class LeaseManager:
    """Single-resource distributed lease coordinator."""

    def __init__(self) -> None:
        self.state: LeaseState = LeaseState.IDLE
        self.holder: str | None = None
        self.token: int = 0
        self.expires_at: int = 0
        self._issued_tokens: dict[str, int] = {}
        self._client_expirations: dict[str, int] = {}

    def expire_check(self, now: int) -> None:
        """Advance state to EXPIRED once current lease passes its deadline."""
        if self.state == LeaseState.HELD and now >= self.expires_at:
            self.state = LeaseState.EXPIRED

    def acquire(self, client_id: str, now: int, ttl: int) -> int | None:
        """Grant a new lease with a fresh fencing token if idle or expired."""
        if ttl <= 0:
            raise ValueError("ttl must be positive")
        self.expire_check(now)
        if self.state in (LeaseState.IDLE, LeaseState.EXPIRED):
            self.token += 1
            self.state = LeaseState.HELD
            self.holder = client_id
            self.expires_at = now + ttl
            self._issued_tokens[client_id] = self.token
            self._client_expirations[client_id] = self.expires_at
            return self.token
        return None

    def renew(self, client_id: str, token: int, now: int, ttl: int) -> bool:
        """Extend an active lease for the current holder with matching token."""
        if ttl <= 0:
            raise ValueError("ttl must be positive")
        self.expire_check(now)
        if self._issued_tokens.get(client_id) == token:
            self.state = LeaseState.HELD
            self.holder = client_id
            self.expires_at = now + ttl
            self._client_expirations[client_id] = self.expires_at
            return True
        return False

    def release(self, client_id: str, token: int, now: int) -> bool:
        """Release the lease if held by client_id with the active fencing token."""
        self.expire_check(now)
        if self.state == LeaseState.HELD and self.holder == client_id and self.token == token:
            self.state = LeaseState.IDLE
            self.holder = None
            self.expires_at = 0
            self._client_expirations.pop(client_id, None)
            return True
        return False

    def active_holders(self, now: int) -> set[str]:
        """Return clients whose granted lease window has not yet expired at `now`."""
        return {
            cid
            for cid, exp in self._client_expirations.items()
            if exp > now
        }
EOF

cat > repo/tests/test_lease.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from lease import LeaseManager, LeaseState


class LeaseManagerTest(unittest.TestCase):
    def test_acquire_and_renew_same_holder_before_expiry(self):
        mgr = LeaseManager()
        tok = mgr.acquire("c1", now=0, ttl=5)
        self.assertEqual(tok, 1)
        self.assertEqual(mgr.state, LeaseState.HELD)
        self.assertTrue(mgr.renew("c1", token=1, now=3, ttl=5))
        self.assertEqual(mgr.active_holders(now=6), {"c1"})

    def test_second_client_acquires_after_expiry(self):
        mgr = LeaseManager()
        tok1 = mgr.acquire("c1", now=0, ttl=2)
        self.assertEqual(tok1, 1)
        self.assertIsNone(mgr.acquire("c2", now=1, ttl=2))
        tok2 = mgr.acquire("c2", now=2, ttl=3)
        self.assertEqual(tok2, 2)
        self.assertEqual(mgr.active_holders(now=2), {"c2"})
EOF

cat > program/validate_brief.md <<'EOF'
# Formal Safety Validation: Distributed Lease Manager

`./repo/src/lease.py` implements `LeaseManager` with states `IDLE`, `HELD`, and `EXPIRED`.

Safety invariant (**mutual exclusion**):
- At any timestamp `now`, at most one client may hold a non-expired lease: `len(mgr.active_holders(now)) <= 1`.
- An expired or superseded client must never be able to renew its stale lease.

Requirements:
1. Write a deterministic exhaustive state-space model checker at `program/check_model.py` (Python stdlib only) that directly exercises `./repo/src/lease.py` across clients `("c1", "c2")`, discrete timestamps, `acquire`, `renew`, `release`, and time advancement:
   - Exit non-zero (e.g. exit 1) when any reachable state violates `len(active_holders(now)) <= 1`.
   - Exit 0 when all reachable states satisfy mutual exclusion (reporting total states explored and `violations: 0`).
2. Run `program/check_model.py` on the original buggy `./repo/src/lease.py` and record the shortest counterexample trace in `program/counterexample.json` containing:
   - `invariant`: description of mutual exclusion invariant
   - `violated`: `true`
   - `active_holders`: list of simultaneous holders in the violating state (`len >= 2`)
   - `steps`: ordered list of `>= 3` transition steps leading to the violation
3. Fix the root cause in `./repo/src/lease.py` without weakening the invariant, and add a unit test in `./repo/tests/test_lease.py` replaying the counterexample trace step by step.
4. Re-run `program/check_model.py` and `python3 -B -m unittest discover -s tests` to prove zero invariant violations across all reachable states and all tests passing.
EOF

git -C repo add .
git -C repo commit -q -m "initial distributed lease manager"
