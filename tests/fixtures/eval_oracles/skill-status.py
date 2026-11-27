"""Separated offline oracle for `skill-status`."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def apply(ws: Path) -> dict[str, object]:
    """Run bundled bin/astack-status against program/LANES.md and report exact states + overdue flag."""
    astack_root = Path(__file__).resolve().parents[3]
    status_bin = astack_root / "bin" / "astack-status"
    proc = subprocess.run(
        [sys.executable, "-B", str(status_bin), str(ws / "program" / "LANES.md"), "--repo", str(ws / "repo")],
        cwd=ws,
        capture_output=True,
        text=True,
        check=True,
    )
    verbatim = proc.stdout.strip()
    attention = (
        "Attention: 1 merged/closed lane (`lane/core`), 2 active/open lanes "
        "(`lane/api` healthy and on track; `lane/index` is overdue — PAST wind-down and limit, started 90m ago)."
    )
    report = f"{verbatim}\n\n{attention}\n"
    (ws / "program" / "STATUS.md").write_text(report, encoding="utf-8")
    return {"final_text": report}
