"""Separated offline oracle for `skill-quickcheck`."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def apply(ws: Path) -> dict[str, object]:
    """Run a single focused read-only check on ./repo and write program/QUICKCHECK.md."""
    repo = ws / "repo"
    repro_cmd = (
        "from src.cache import Cache; "
        "c = Cache(2); c.put('a', 1); c.put('a', 2); c.put('b', 3); "
        "assert c.get('a') == 2 and c.get('b') == 3, (c.get('a'), c.get('b'))"
    )
    proc = subprocess.run(
        [sys.executable, "-B", "-c", repro_cmd],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0, f"expected repro to fail on buggy src/cache.py, got rc={proc.returncode}"

    report = f"""VERDICT: BLOCKED: Updating an existing key in `src/cache.py` duplicates it in `_order` and evicts live entries early.

BLOCKING (P0–P2)
- [P1] `Cache.put` in `src/cache.py` violates the AD-001 contract in `docs/ARCHITECTURE.md`: overwriting an existing key unconditionally appends a duplicate entry to `self._order`, so `len(self._order) > self.capacity` pops and deletes a live key even when only 2 distinct keys exist for `capacity=2`. Reproduce/Citation: `python3 -c "{repro_cmd}"` exits `{proc.returncode}` (`{proc.stderr.strip().splitlines()[-1]}`). Cause: the change. Fix: only append `key` to `self._order` and evict when `key not in self._data`.

HELD
- `python3 -m unittest discover -s tests` passes existing FIFO test cases.
- Documented FIFO eviction, single-threaded design (`docs/ARCHITECTURE.md`), and `DATA_DIR` startup default (`README.md`, `scripts/run.sh`) match known project decisions and tooling; omitted as non-issues.

COULD NOT TEST
- none
"""
    (ws / "program" / "QUICKCHECK.md").write_text(report, encoding="utf-8")
    return {
        "final_text": (
            "Quickcheck found one verified blocker in `src/cache.py` (`Cache.put` duplicates existing keys "
            "in `_order`, prematurely evicting live entries in violation of `docs/ARCHITECTURE.md` AD-001) "
            "and saved the report to `program/QUICKCHECK.md`. Documented FIFO/single-threaded choices and "
            "`DATA_DIR` startup tooling defaults were not flagged."
        ),
        "events": [
            {"type": "tool_use", "name": "Read", "input": {"file_path": "skills/quickcheck/SKILL.md"}},
        ],
    }
