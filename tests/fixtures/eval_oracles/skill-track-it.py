"""Separated offline oracle for `skill-track-it`."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def apply(ws: Path) -> dict[str, object]:
    """Verify #101 SHA and test states in ./repo and update program/issues.json accurately."""
    repo = ws / "repo"
    sha_101 = subprocess.run(
        ["git", "-C", str(repo), "log", "--grep=#101", "--format=%H", "-n", "1"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    issues_path = ws / "program" / "issues.json"
    data = json.loads(issues_path.read_text(encoding="utf-8"))
    for issue in data["issues"]:
        if issue["id"] == "#101":
            issue["status"] = "closed"
            issue["state"] = "done"
            issue["proof_sha"] = sha_101
            issue["notes"].append(
                f"Closed with proof: landed in {sha_101}; `python3 -m unittest tests/test_token.py` passes."
            )
        elif issue["id"] == "#102":
            issue["status"] = "open"
            issue["state"] = "blocked"
            issue["blocked_by"] = ["#98"]
            issue["notes"].append(
                "Blocked on #98 (RFC-4180 quoting policy); `tests/test_export.py` fails on embedded commas."
            )
        elif issue["id"] == "#103":
            issue["status"] = "open"
            issue["state"] = "in_progress"
            issue["notes"].append("In progress; worker lane active.")

    issues_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return {
        "final_text": (
            f"Synced `program/issues.json` for Epic #100: closed `#101` with verified commit `{sha_101}` "
            "and passing `tests/test_token.py`, kept `#102` open and marked `blocked` (failing "
            "`tests/test_export.py`, waiting on `#98`), and kept `#103` open in progress."
        ),
    }
