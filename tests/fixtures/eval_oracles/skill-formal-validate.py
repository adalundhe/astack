"""Separated offline oracle for `skill-formal-validate`."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_CHECK_MODEL_SCRIPT = '''#!/usr/bin/env python3
"""Deterministic exhaustive BFS model checker for repo/src/lease.py."""
from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import deque
from pathlib import Path

WS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WS / "repo" / "src"))
from lease import LeaseManager

CLIENTS = ("c1", "c2")
TTL = 2
MAX_TIME = 4
MAX_TOKENS = 3


def _state_key(mgr: LeaseManager, now: int) -> tuple[object, ...]:
    return (
        now,
        mgr.state.value,
        mgr.holder,
        mgr.token,
        mgr.expires_at,
        tuple(sorted(mgr._issued_tokens.items())),
        tuple(sorted(mgr._client_expirations.items())),
    )


def explore() -> dict[str, object]:
    init = LeaseManager()
    start_key = _state_key(init, 0)
    queue: deque[tuple[LeaseManager, int, list[dict[str, object]]]] = deque([(init, 0, [])])
    visited: set[tuple[object, ...]] = {start_key}

    while queue:
        mgr, now, trace = queue.popleft()
        holders = sorted(mgr.active_holders(now))
        if len(holders) > 1:
            return {
                "invariant": "mutual_exclusion: len(active_holders(now)) <= 1",
                "violated": True,
                "states_explored": len(visited),
                "now": now,
                "active_holders": holders,
                "steps": trace,
            }

        transitions: list[tuple[str, dict[str, object], LeaseManager, int]] = []

        # Action 1: advance clock by 1 up to MAX_TIME
        if now < MAX_TIME:
            nxt = copy.deepcopy(mgr)
            nxt_now = now + 1
            nxt.expire_check(nxt_now)
            transitions.append((
                "tick",
                {"action": "tick", "now": nxt_now, "state": nxt.state.value},
                nxt,
                nxt_now,
            ))

        # Action 2: acquire for each client (bounded token budget)
        if mgr.token < MAX_TOKENS:
            for cid in CLIENTS:
                nxt = copy.deepcopy(mgr)
                tok = nxt.acquire(cid, now=now, ttl=TTL)
                if tok is not None:
                    transitions.append((
                        "acquire",
                        {"action": "acquire", "client": cid, "now": now, "ttl": TTL, "token": tok},
                        nxt,
                        now,
                    ))

        # Action 3: renew for any client holding any previously issued token
        for cid, tok in sorted(mgr._issued_tokens.items()):
            nxt = copy.deepcopy(mgr)
            ok = nxt.renew(cid, token=tok, now=now, ttl=TTL)
            if ok:
                transitions.append((
                    "renew",
                    {"action": "renew", "client": cid, "token": tok, "now": now, "ttl": TTL, "accepted": True},
                    nxt,
                    now,
                ))

        # Action 4: release for current holder
        if mgr.holder is not None:
            cid = mgr.holder
            tok = mgr.token
            nxt = copy.deepcopy(mgr)
            if nxt.release(cid, token=tok, now=now):
                transitions.append((
                    "release",
                    {"action": "release", "client": cid, "token": tok, "now": now},
                    nxt,
                    now,
                ))

        for _, step_info, nxt_mgr, nxt_now in transitions:
            key = _state_key(nxt_mgr, nxt_now)
            if key not in visited:
                visited.add(key)
                queue.append((nxt_mgr, nxt_now, [*trace, step_info]))

    return {
        "invariant": "mutual_exclusion: len(active_holders(now)) <= 1",
        "violated": False,
        "violations": 0,
        "states_explored": len(visited),
        "bounds": {"clients": list(CLIENTS), "ttl": TTL, "max_time": MAX_TIME, "max_tokens": MAX_TOKENS},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="", help="Optional path to write JSON report")
    args = parser.parse_args()
    result = explore()
    text = json.dumps(result, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\\n", encoding="utf-8")
    print(text)
    return 1 if result["violated"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

_FIXED_LEASE_SRC = '''"""Distributed lease state machine with fencing tokens."""
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
        """Extend an active lease only for the current non-expired holder with the active token."""
        if ttl <= 0:
            raise ValueError("ttl must be positive")
        self.expire_check(now)
        if (
            self.state == LeaseState.HELD
            and self.holder == client_id
            and self.token == token
            and now < self.expires_at
        ):
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
'''

_TEST_LEASE_SRC = '''import sys
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

    def test_counterexample_replay_expired_holder_cannot_renew_after_handover(self):
        mgr = LeaseManager()
        tok1 = mgr.acquire("c1", now=0, ttl=2)
        self.assertEqual(tok1, 1)
        mgr.expire_check(now=2)
        self.assertEqual(mgr.state, LeaseState.EXPIRED)
        tok2 = mgr.acquire("c2", now=2, ttl=3)
        self.assertEqual(tok2, 2)
        self.assertFalse(mgr.renew("c1", token=tok1, now=3, ttl=3))
        self.assertEqual(mgr.active_holders(now=3), {"c2"})

    def test_expired_holder_cannot_renew_without_reacquiring(self):
        mgr = LeaseManager()
        tok1 = mgr.acquire("c1", now=0, ttl=2)
        self.assertFalse(mgr.renew("c1", token=tok1, now=2, ttl=2))
        self.assertEqual(mgr.active_holders(now=2), set())
'''


def apply(ws: Path) -> dict[str, object]:
    """Write BFS model checker, record buggy counterexample, fix lease.py + tests, confirm 0 violations."""
    checker = ws / "program" / "check_model.py"
    ce_path = ws / "program" / "counterexample.json"
    checker.write_text(_CHECK_MODEL_SCRIPT, encoding="utf-8")

    # Capture counterexample on buggy root code
    buggy_run = subprocess.run(
        [sys.executable, "-B", str(checker), "--out", str(ce_path)],
        cwd=ws,
        capture_output=True,
        text=True,
    )
    assert buggy_run.returncode != 0, "expected checker to find violation on buggy lease.py"

    # Fix lease.py and replay counterexample in unit tests
    (ws / "repo" / "src" / "lease.py").write_text(_FIXED_LEASE_SRC, encoding="utf-8")
    (ws / "repo" / "tests" / "test_lease.py").write_text(_TEST_LEASE_SRC, encoding="utf-8")

    # Re-run exhaustive checker and unit tests
    fixed_run = subprocess.run(
        [sys.executable, "-B", str(checker)],
        cwd=ws,
        capture_output=True,
        text=True,
        check=True,
    )
    subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests"],
        cwd=ws / "repo",
        capture_output=True,
        text=True,
        check=True,
    )
    summary = json.loads(fixed_run.stdout)
    return {
        "final_text": (
            f"Built exhaustive BFS state-space model checker `program/check_model.py`, captured the mutual-exclusion "
            f"counterexample trace in `program/counterexample.json`, fixed `renew()` in `./repo/src/lease.py` to "
            f"require active `HELD` state with matching current holder/token before expiry, added the replay test in "
            f"`./repo/tests/test_lease.py`, and verified 0 violations across {summary['states_explored']} reachable states."
        ),
    }
