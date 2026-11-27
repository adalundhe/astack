"""Separated offline oracle for `skill-slates`."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def apply(ws: Path) -> dict[str, object]:
    """Provision two isolated git worktrees outside ./repo and record them in program/workspaces.json."""
    repo = ws / "repo"
    wt_root = ws / "program" / "worktrees"
    wt_root.mkdir(parents=True, exist_ok=True)
    auth_dir = wt_root / "auth"
    billing_dir = wt_root / "billing"

    subprocess.run(
        ["git", "-C", str(repo), "worktree", "add", str(auth_dir), "-b", "lane/auth"],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "worktree", "add", str(billing_dir), "-b", "lane/billing"],
        check=True,
        capture_output=True,
        text=True,
    )

    manifest = {
        "backend": "git-worktree",
        "base_repo": "repo",
        "workspaces": [
            {
                "lane": "lane/auth",
                "branch": "lane/auth",
                "path": "program/worktrees/auth",
                "backend": "git-worktree",
            },
            {
                "lane": "lane/billing",
                "branch": "lane/billing",
                "path": "program/worktrees/billing",
                "backend": "git-worktree",
            },
        ],
    }
    (ws / "program" / "workspaces.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "final_text": (
            "Slates daemon is unavailable in this environment, so I fell back to git worktrees and "
            "provisioned `program/worktrees/auth` (`lane/auth`) and `program/worktrees/billing` (`lane/billing`) "
            "outside `./repo`, keeping `./repo` clean on `main` and recording both paths in `program/workspaces.json`."
        ),
    }
