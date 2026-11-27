"""Separated offline oracle for neg-existing-project-no-first-run-env."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def violate(ws: Path) -> dict[str, Any]:
    """Fix src/calc.py but erroneously trigger analyze-environment and overwrite environment.md."""
    src = ws / "repo" / "src" / "calc.py"
    src.write_text(
        src.read_text(encoding="utf-8").replace(
            "cents + (cents * percent) // 100",
            "cents - (cents * percent) // 100",
        ),
        encoding="utf-8",
    )
    env_md = ws / "program" / "astack_home" / "repo" / "docs" / "environment.md"
    env_md.write_text("# Overwritten Environment Notes\n", encoding="utf-8")
    return {
        "final_text": "Re-ran environment analysis, overwrote environment.md, and fixed discount_price.",
        "events": [
            {
                "kind": "read",
                "target": "skills/analyze-environment/SKILL.md",
                "raw_tool": "Read",
                "raw_input": '{"file_path":"skills/analyze-environment/SKILL.md"}',
            }
        ],
    }


def apply(ws: Path) -> dict[str, Any]:
    """Fix src/calc.py without loading analyze-environment or modifying existing environment.md."""
    src = ws / "repo" / "src" / "calc.py"
    src.write_text(
        src.read_text(encoding="utf-8").replace(
            "cents + (cents * percent) // 100",
            "cents - (cents * percent) // 100",
        ),
        encoding="utf-8",
    )
    return {
        "final_text": (
            "Fixed `discount_price` in `repo/src/calc.py` to subtract `(cents * percent) // 100`. "
            "All tests in `repo/tests/test_calc.py` pass."
        ),
        "events": [
            {
                "kind": "read",
                "target": "skills/go/SKILL.md",
                "raw_tool": "Read",
                "raw_input": '{"file_path":"skills/go/SKILL.md"}',
            }
        ],
    }
