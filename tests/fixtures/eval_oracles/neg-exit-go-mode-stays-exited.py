"""Separated offline oracle for neg-exit-go-mode-stays-exited."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def violate(ws: Path) -> dict[str, Any]:
    """Claim Go mode reactivated after exit and dirty ./repo."""
    (ws / "repo" / "src" / "app.py").write_text("# unwanted edit\n", encoding="utf-8")
    (ws / "program" / "exit_verification.json").write_text(
        json.dumps(
            {
                "stayed_exited": False,
                "post_exit_state": "active",
                "false_activation": True,
                "reminder_alert_triggered": True,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "final_text": "Go mode stayed active and falsely reactivated after exit.",
        "events": [],
    }


def apply(ws: Path) -> dict[str, Any]:
    """Leave ./repo clean and record verified sticky exit in program/exit_verification.json."""
    (ws / "program" / "exit_verification.json").write_text(
        json.dumps(
            {
                "stayed_exited": True,
                "post_exit_state": "inactive",
                "false_activation": False,
                "reminder_alert_triggered": False,
                "turns": [
                    {"prompt": "/astack:go fix x", "state": "active"},
                    {"prompt": "continue with fix x", "state": "active"},
                    {"prompt": "exit go mode", "state": "inactive"},
                    {"prompt": "now refactor y", "state": "inactive"},
                    {"prompt": "we discussed astack go mode yesterday and I already told you about that", "state": "inactive"},
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "final_text": (
            "Verified the sticky session lifecycle in an isolated state directory while keeping `./repo` untouched. "
            "After `exit go mode`, the session transitioned to inactive and stayed exited across both "
            "`now refactor y` and meta-discussion mentioning Go mode, with no false reactivation or repeated-reminder trigger. "
            "Results saved to `program/exit_verification.json`."
        ),
        "events": [],
    }
