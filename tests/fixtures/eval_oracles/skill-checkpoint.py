"""Separated offline oracle for `skill-checkpoint`."""
from __future__ import annotations

import subprocess
from pathlib import Path


def apply(ws: Path) -> dict[str, object]:
    """Write durable program/CHECKPOINT.md for lane/billing without modifying repo."""
    repo = ws / "repo"
    branch = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    sha = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    checkpoint_md = (
        "# Checkpoint: Billing Lane\n\n"
        f"- **Branch:** `{branch}`\n"
        f"- **Commit SHA:** `{sha}`\n"
        "- **Mode:** `agentic-only`\n\n"
        "## Completed Work\n"
        f"- Step 1 committed at `{sha[:7]}`: implemented `add_line_item` subtotal calculation in "
        "`repo/src/billing.py` with unit tests in `repo/tests/test_billing.py`.\n\n"
        "## Remaining Work\n"
        "- Step 2: implement `apply_discount(subtotal_cents, pct)` in `repo/src/billing.py` with "
        "percentage bounds validation and unit tests in `repo/tests/test_billing.py`.\n\n"
        "## Verification Command\n"
        "```bash\n"
        "python3 -B -m unittest discover -s tests\n"
        "```\n"
    )
    (ws / "program" / "CHECKPOINT.md").write_text(checkpoint_md, encoding="utf-8")
    return {
        "final_text": (
            f"Saved durable checkpoint to `program/CHECKPOINT.md` for `{branch}` at `{sha[:7]}` "
            "(step 1 `add_line_item` complete, step 2 `apply_discount` remaining, verified with "
            "`python3 -B -m unittest discover -s tests`). `./repo` remains clean."
        ),
    }
