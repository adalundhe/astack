"""Separated offline oracle for `skill-cross-repo`."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def _head_sha(repo: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def apply(ws: Path) -> dict[str, object]:
    """Rewrite program/release-plan.json with exact pinned SHAs and repo-lib before repo-app."""
    lib_sha = _head_sha(ws / "repo-lib")
    app_sha = _head_sha(ws / "repo-app")
    fixed_plan = {
        "name": "pricing-tax-rollout",
        "goal": "Roll out tax_rate_bps support in pricing_lib and checkout-app without breaking live callers.",
        "rollback_order": ["deploy-app", "release-lib"],
        "steps": [
            {
                "id": "release-lib",
                "repo": "repo-lib",
                "phase": "expand",
                "ref": lib_sha,
                "depends_on": [],
                "outputs": {"commit_sha": lib_sha},
                "verify_cmd": "python3 -m unittest discover -s tests",
                "rollback_note": "Rollback repo-lib only after deploy-app has rolled back.",
            },
            {
                "id": "deploy-app",
                "repo": "repo-app",
                "phase": "switch",
                "ref": app_sha,
                "depends_on": ["release-lib"],
                "outputs": {"commit_sha": app_sha},
                "verify_cmd": "python3 -m unittest discover -s tests",
                "rollback_note": "Rollback repo-app first so callers stop passing tax_rate_bps before reverting repo-lib.",
            },
        ],
    }
    (ws / "program" / "release-plan.json").write_text(
        json.dumps(fixed_plan, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "final_text": (
            f"Updated `program/release-plan.json`: ordered `release-lib` ({lib_sha}) before "
            f"`deploy-app` ({app_sha}), pinned exact git SHAs in place of floating `main`/`latest` refs, "
            "and set reverse-order rollback notes (`deploy-app` before `release-lib`)."
        ),
    }
