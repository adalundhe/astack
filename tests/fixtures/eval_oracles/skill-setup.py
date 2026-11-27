"""Separated offline oracle for `skill-setup`."""
from __future__ import annotations

import json
from pathlib import Path

UPDATED_SETTINGS = {
    "worker_minutes": 60,
    "reviewer_minutes": 30,
    "researcher_minutes": 30,
    "wind_down_minutes": 5,
    "check_in_minutes": 5,
    "roles": {
        "lead": {"provider": "anthropic", "model": "opus", "effort": "high"},
        "worker": {"provider": "anthropic", "model": "sonnet", "effort": "medium"},
        "researcher": {"provider": "anthropic", "model": "haiku", "effort": "medium"},
    },
    "reviewer_pool": [
        {"provider": "openai", "model": "gpt-5.4", "effort": "high"},
        {"provider": "anthropic", "model": "sonnet", "effort": "high"},
    ],
    "autonomy": {
        "mode": "supervised",
        "allow": [],
        "deny": [
            "merge_pr",
            "push_protected_branch",
            "close_or_delete_others_pr",
            "prod_deploy_or_destructive_migration",
            "spend_money_or_billing_changes",
            "publish_external_release",
            "weaken_verification_gates",
        ],
    },
    "automation": {
        "mode": "agentic-only",
    },
}


def apply(ws: Path) -> dict[str, object]:
    """Migrate legacy program/settings.json to the full validated configuration."""
    (ws / "program" / "settings.json").write_text(
        json.dumps(UPDATED_SETTINGS, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "final_text": (
            "Updated `program/settings.json`: added `reviewer_minutes` (30) and `researcher_minutes` (30), "
            "migrated the legacy reviewer entry into the approved reviewers list alongside Anthropic Sonnet, "
            "configured `supervised` autonomy with default deny safeguards, set `agentic-only` automation, "
            "and left `./repo` untouched."
        ),
    }
