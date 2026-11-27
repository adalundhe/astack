"""Separated offline oracle for `skill-risk-modeling`."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def apply(ws: Path) -> dict[str, object]:
    """Run baseline scorer on ./repo and write program/RISK_SCORE.json without touching ./repo."""
    inp = json.dumps({
        "vectors": [
            {"name": "core", "files": ["src/core.py"]},
            {"name": "docs", "files": ["README.md"]},
        ]
    })
    proc = subprocess.run(
        [
            sys.executable, "-B", str(ROOT / "bin" / "astack-review-ledger"),
            "score", "-", "--repo", str(ws / "repo"), "--base", "main~1", "--head", "HEAD", "--horizon", "2", "--json",
        ],
        input=inp,
        capture_output=True,
        text=True,
        check=True,
    )
    out = ws / "program" / "RISK_SCORE.json"
    out.write_text(proc.stdout, encoding="utf-8")
    data = json.loads(proc.stdout)
    return {
        "final_text": (
            f"Scored `core` and `docs` into `program/RISK_SCORE.json` using the git baseline "
            f"(change_risk={data['change_risk']}, level_status=unverified — authorizes shares, not absolute level)."
        ),
        "events": [
            {"type": "tool_use", "name": "Read", "input": {"file_path": "skills/risk-modeling/SKILL.md"}},
        ],
    }
