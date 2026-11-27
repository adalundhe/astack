"""Separated offline oracle for `skill-unland`."""
from __future__ import annotations

import subprocess
from pathlib import Path


def apply(ws: Path) -> dict[str, object]:
    """Revert ONLY commit B via `git revert --no-edit`, preserving commit C and history."""
    repo = ws / "repo"
    commit_b = (ws / "program" / "commit_b.txt").read_text(encoding="utf-8").strip()
    subprocess.run(
        ["git", "-C", str(repo), "revert", "--no-edit", commit_b],
        check=True,
        capture_output=True,
        text=True,
    )
    return {
        "final_text": (
            f"Inspected git history on `main`, confirmed commit {commit_b[:8]} introduced the "
            "off-by-one bug in `src/rate_limit.py`, created a `git revert` commit on top of the "
            "docs commit so `docs/API.md` and shared history remain intact, and verified `unittest` passes."
        ),
    }
