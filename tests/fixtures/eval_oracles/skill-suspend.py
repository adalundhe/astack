"""Separated offline oracle for `skill-suspend`."""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path


def apply(ws: Path) -> dict[str, object]:
    """Commit green WIP edits on lane/sync, stamp pause line in LANES.md, and write SUSPENDED.md."""
    repo = ws / "repo"
    subprocess.run(["git", "-C", str(repo), "add", "src/sync.py", "tests/test_sync.py"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", "wip(sync): add checkpoint_offset helper and unit test"],
        check=True,
    )
    sha = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    lanes_path = ws / "program" / "LANES.md"
    existing = lanes_path.read_text(encoding="utf-8")
    prefix = "" if existing.endswith("\n") else "\n"
    lanes_path.write_text(
        existing + prefix + f"{stamp} paused w1 on lane/sync at {sha[:7]} (green WIP committed; step 2 pending)\n",
        encoding="utf-8",
    )

    suspended_md = (
        "# Suspended Lane: lane/sync\n\n"
        "- **Status:** PAUSED\n"
        "- **Branch:** `lane/sync`\n"
        f"- **Saved Commit SHA:** `{sha}`\n"
        f"- **Paused At (UTC):** `{stamp}`\n\n"
        "## Saved Progress\n"
        "- Step 1 (`checkpoint_offset` helper and unit tests) committed green on `lane/sync`.\n"
        "- Remaining: Step 2 (add retry cap in `src/sync.py` with unit tests).\n\n"
        "## Exact Resume Command\n"
        "```bash\n"
        "git -C repo checkout lane/sync && python3 -B -m unittest discover -s repo/tests\n"
        "```\n"
    )
    (ws / "program" / "SUSPENDED.md").write_text(suspended_md, encoding="utf-8")
    return {
        "final_text": (
            f"Suspended `lane/sync` cleanly: committed green WIP (`checkpoint_offset` + tests) at `{sha[:7]}`, "
            f"appended UTC-stamped pause entry `{stamp}` in `program/LANES.md`, and wrote resume handoff to `program/SUSPENDED.md`."
        ),
    }
