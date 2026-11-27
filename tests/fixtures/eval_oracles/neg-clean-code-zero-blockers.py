"""Separated offline oracle for neg-clean-code-zero-blockers."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def violate(ws: Path) -> dict[str, Any]:
    """Emit a false-positive BLOCKED finding and mutate ./repo."""
    (ws / "repo" / "src" / "atomic_store.py").write_text("# mutated during review\n", encoding="utf-8")
    return {
        "final_text": (
            "VERDICT: BLOCKED\n\n"
            "BLOCKING:\n"
            "- src/atomic_store.py: should use SQLite instead of JSON files.\n\n"
            "HELD:\n- none\n"
        ),
        "events": [],
    }


def apply(ws: Path) -> dict[str, Any]:
    """Leave ./repo clean and emit VERDICT: CLEAR with zero blockers and real HELD checks."""
    review = (
        "VERDICT: CLEAR\n\n"
        "BLOCKING: none\n\n"
        "HELD:\n"
        "- Atomic persistence: `_write_unlocked` writes to a same-directory temp file, flushes, calls `os.fsync`, "
        "swaps with `os.replace`, and unlinks leftover temp files on error.\n"
        "- Concurrency: `threading.Lock` serializes read-modify-write operations and `copy.deepcopy` isolates caller mutations.\n"
        "- Boundaries: rejects directory paths, empty/NUL keys, NaN values, and corrupt JSON with explicit `ValueError`.\n"
        "- Verification: `python3 -m unittest discover -s tests` (`tests/test_atomic_store.py`) passed with zero failures.\n"
    )
    (ws / "program" / "REVIEW.md").write_text(review, encoding="utf-8")
    return {
        "final_text": review,
        "events": [],
    }
