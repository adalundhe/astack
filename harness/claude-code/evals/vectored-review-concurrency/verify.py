#!/usr/bin/env python3
"""Objective post-run verifier for vectored-review-concurrency.

Verifies repo/ was untouched AND at least one saved reproduction script fails on the
buggy split-lock `JobPool.drain_batch` and passes on the single-lock fixed version.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _repro_verify import PlantedBug, verify_reproductions  # noqa: E402


def fix_split_lock_drain_batch(repo: Path) -> None:
    p = repo / "pool.py"
    text = p.read_text(encoding="utf-8")
    old = (
        "        with self._lock:\n"
        "            batch = list(self._items[:limit])\n"
        "        with self._lock:\n"
        "            del self._items[: len(batch)]\n"
        "            self.drained += len(batch)"
    )
    new = (
        "        with self._lock:\n"
        "            batch = list(self._items[:limit])\n"
        "            del self._items[: len(batch)]\n"
        "            self.drained += len(batch)"
    )
    assert old in text, "drain_batch anchor missing in pool.py"
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


PLANTED_BUGS = [
    PlantedBug(
        "bug1_split_lock_drain_batch",
        "JobPool.drain_batch releases lock between slice and delete",
        fix_split_lock_drain_batch,
        attempts=3,
    ),
]


def main() -> int:
    ws = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    code, _ = verify_reproductions(ws, PLANTED_BUGS, min_proven=1)
    return code


if __name__ == "__main__":
    sys.exit(main())
