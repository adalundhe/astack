#!/usr/bin/env python3
"""Objective post-run verifier for vectored-review-cross-harness.

Verifies repo/ was untouched AND saved reproduction scripts fail on the buggy `auth.py`
and pass on the fixed version (requiring objective proof of the expired-refreshed-token bug,
and also tracking proof of the non-constant-time signature comparison bug).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _repro_verify import PlantedBug, verify_reproductions  # noqa: E402


def fix_bug1_expired_refresh(repo: Path) -> None:
    p = repo / "auth.py"
    text = p.read_text(encoding="utf-8")
    old = '    if tag != "r" and expires_at <= now_ts:\n        return None'
    new = "    if expires_at <= now_ts:\n        return None"
    assert old in text, "bug1 anchor missing in auth.py"
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


def fix_bug2_timing_compare(repo: Path) -> None:
    p = repo / "auth.py"
    text = p.read_text(encoding="utf-8")
    old = "    if expected != sig:\n        return None"
    new = "    if not hmac.compare_digest(expected, sig):\n        return None"
    assert old in text, "bug2 anchor missing in auth.py"
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


PLANTED_BUGS = [
    PlantedBug("bug1_expired_refresh", "verify_token skips expiry check for refreshed tokens", fix_bug1_expired_refresh, attempts=1),
    PlantedBug("bug2_timing_compare", "verify_token uses != instead of hmac.compare_digest", fix_bug2_timing_compare, attempts=1),
]


def main() -> int:
    ws = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    code, _ = verify_reproductions(ws, PLANTED_BUGS, min_proven=1, require_all=("bug1_expired_refresh",))
    return code


if __name__ == "__main__":
    sys.exit(main())
