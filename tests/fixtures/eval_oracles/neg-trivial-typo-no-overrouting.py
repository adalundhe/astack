"""Separated offline oracle for neg-trivial-typo-no-overrouting."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def violate(ws: Path) -> dict[str, Any]:
    """Fix the typo but over-route by creating program/DAG.md and loading heavy skills."""
    src = ws / "repo" / "src" / "greeting.py"
    src.write_text(src.read_text(encoding="utf-8").replace("Helo, ", "Hello, "), encoding="utf-8")
    (ws / "program" / "DAG.md").write_text("# DAG\n\n- Wave 1: fix greeting typo\n", encoding="utf-8")
    return {
        "final_text": "Built a multi-wave DAG in program/DAG.md and fixed the greeting typo.",
        "events": [
            {"kind": "read", "target": "skills/dagify/SKILL.md", "raw_tool": "Read", "raw_input": '{"file_path":"skills/dagify/SKILL.md"}'},
            {"kind": "read", "target": "skills/bugbash/SKILL.md", "raw_tool": "Read", "raw_input": '{"file_path":"skills/bugbash/SKILL.md"}'},
        ],
    }


def apply(ws: Path) -> dict[str, Any]:
    """Fix only the single typo in src/greeting.py without heavy workflow overhead."""
    src = ws / "repo" / "src" / "greeting.py"
    src.write_text(src.read_text(encoding="utf-8").replace("Helo, ", "Hello, "), encoding="utf-8")
    return {
        "final_text": 'Fixed the `"Helo, "` typo to `"Hello, "` in `repo/src/greeting.py`; `tests/test_greeting.py` passes.',
        "events": [
            {"kind": "read", "target": "skills/go/SKILL.md", "raw_tool": "Read", "raw_input": '{"file_path":"skills/go/SKILL.md"}'},
        ],
    }
