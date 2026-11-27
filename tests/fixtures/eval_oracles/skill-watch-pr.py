"""Separated offline oracle for `skill-watch-pr`."""
from __future__ import annotations

import json
from pathlib import Path


def apply(ws: Path) -> dict[str, object]:
    """Assess program/pr_state.json and write program/pr_action.json without modifying repo."""
    state = json.loads((ws / "program" / "pr_state.json").read_text(encoding="utf-8"))
    action = {
        "pr_number": state["pr_number"],
        "branch": state["branch"],
        "head_sha": state["head_sha"],
        "merge_ready": False,
        "status": "blocked",
        "blockers": [
            {
                "kind": "ci_failed",
                "check": "unit-tests",
                "details": "unit-tests check failed: AssertionError in tests/test_auth.py::test_expired_token_rejected",
            },
            {
                "kind": "unresolved_review_thread",
                "thread_id": "RT_42_1",
                "location": "src/auth.py:18",
                "details": "Blocking thread on src/auth.py:18 requires strict `<` comparison for exclusive expires_at.",
            },
        ],
        "remediation": [
            "Fix the exclusive expiry boundary check at src/auth.py:18 so unit-tests passes.",
            "Reply with verification evidence on review thread RT_42_1 (src/auth.py:18) and resolve the thread after replying.",
            "Re-run tests and re-check PR #42 readiness before merging.",
        ],
    }
    (ws / "program" / "pr_action.json").write_text(json.dumps(action, indent=2) + "\n", encoding="utf-8")
    return {
        "final_text": (
            f"PR #42 ({state['branch']} @ {state['head_sha'][:7]}) is not merge_ready (status: blocked). "
            "Blockers: failing CI check `unit-tests` and unresolved blocking review thread RT_42_1 at `src/auth.py:18`. "
            "Recorded blockers and remediation steps in `program/pr_action.json`; `./repo` left untouched."
        ),
    }
