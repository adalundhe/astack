"""Separated offline oracle for `skill-rtfm`."""
from __future__ import annotations

import subprocess
from pathlib import Path


def violate(ws: Path) -> dict[str, object]:
    """Return a drive-by deflection that fails to check docs or git history."""
    return {
        "final_text": (
            "I cannot tell why MAX_RETRIES is set to 3 from a quick glance. "
            "Yes, you should ask the author why they chose 3."
        ),
    }


def apply(ws: Path) -> dict[str, object]:
    """Read docs/AD-007.md and git log to answer directly with exact citations."""
    repo = ws / "repo"
    sha = subprocess.run(
        ["git", "-C", str(repo), "log", "--grep=AD-007", "--format=%h", "-n", "1"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    return {
        "final_text": (
            "No need to ask the author — this is already settled in the repo.\n\n"
            "`MAX_RETRIES` is capped at `3` in `src/retry.py:4` because the upstream API enforces a strict 429 ban on the 4th attempt "
            "(locking out the client IP for 15 minutes). Stopping at 3 retries absorbs transient 5xx errors without triggering the ban.\n\n"
            f"- Documented in: `docs/AD-007.md`\n"
            f"- Lowered from `5` to `3` in commit: `{sha}`"
        ),
    }
