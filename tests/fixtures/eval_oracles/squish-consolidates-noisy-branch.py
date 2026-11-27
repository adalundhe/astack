"""Separated offline oracle for `squish-consolidates-noisy-branch`."""
from __future__ import annotations

import subprocess
from pathlib import Path


def apply(ws: Path) -> dict[str, object]:
    """Consolidate the 6 noisy branch commits into 1 while keeping the tree identical and crediting Bob."""
    repo = ws / "repo"
    base_sha = (ws / "program" / "base_sha.txt").read_text(encoding="utf-8").strip()
    subprocess.run(["git", "-C", str(repo), "reset", "--soft", base_sha], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "commit",
            "-q",
            "-m",
            "feat: add cap and jitter to backoff\n\nCo-authored-by: Bob <bob@example.invalid>",
        ],
        check=True,
    )
    return {
        "final_text": (
            "Consolidated 6 commits on feat/retry-jitter into 1 commit on top of main, "
            "preserving identical tree contents and Bob's authorship credit."
        ),
    }
