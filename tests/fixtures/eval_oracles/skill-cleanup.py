"""Separated offline oracle for `skill-cleanup`."""
from __future__ import annotations

from pathlib import Path


def apply(ws: Path) -> dict[str, object]:
    """Delete the 3 untracked repo scratch files while strictly preserving tracked files and ASTACK_HOME bundles."""
    repo = ws / "repo"
    for rel in ("debug_tmp.log", "scratch_repro.py", ".tmp_trace"):
        target = repo / rel
        if target.exists():
            target.unlink()
    return {
        "final_text": (
            "Removed temporary scratch files from `./repo`: `debug_tmp.log`, `scratch_repro.py`, `.tmp_trace`. "
            "Kept tracked files (`src/invoice.py`, `tests/test_invoice.py`) and preserved durable bundles under "
            "`program/astack_home/billing/` (`reviews/2026-11-25T10-00-00Z/proof.txt` and `repros/repro_bug.py`). "
            "Verified `git status` is clean and unit tests pass."
        ),
    }
