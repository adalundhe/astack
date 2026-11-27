#!/usr/bin/env python3
"""Executable verifier for `skill-watch-pr`."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _serialize_item(item: object) -> str:
    if isinstance(item, str):
        return item
    return json.dumps(item, sort_keys=True)


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    state_path = ws / "program" / "pr_state.json"
    action_path = ws / "program" / "pr_action.json"
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir() or not state_path.is_file():
        checks.append(("workspace-intact", False, "missing repo or program/pr_state.json"))
        return _eval_kit.report_and_exit(checks)

    pr_state = json.loads(state_path.read_text(encoding="utf-8"))
    expected_sha = pr_state["head_sha"]

    clean_ok, clean_detail = _eval_kit.check_git_clean(repo)
    checks.append(("git-clean", clean_ok, clean_detail))

    head_sha = _git(repo, "rev-parse", "HEAD")
    checks.append((
        "repo-head-unchanged",
        head_sha == expected_sha,
        f"HEAD={head_sha[:7]} matches expected {expected_sha[:7]}" if head_sha == expected_sha else f"HEAD changed to {head_sha}",
    ))

    if not action_path.is_file():
        checks.append(("pr-action-exists", False, "missing program/pr_action.json"))
        return _eval_kit.report_and_exit(checks)

    action_raw = action_path.read_text(encoding="utf-8")
    try:
        action = json.loads(action_raw)
    except json.JSONDecodeError as exc:
        checks.append(("pr-action-json", False, f"invalid JSON: {exc}"))
        return _eval_kit.report_and_exit(checks)

    if not isinstance(action, dict):
        checks.append(("pr-action-object", False, "program/pr_action.json must be a JSON object"))
        return _eval_kit.report_and_exit(checks)
    checks.append(("pr-action-object", True, "valid JSON object"))

    pr_num = action.get("pr_number")
    pr_ok = pr_num == 42 or str(pr_num) == "42"
    checks.append(("pr-number", pr_ok, f"pr_number={pr_num!r}"))

    merge_ready = action.get("merge_ready")
    status_val = str(action.get("status") or action.get("state") or "").strip().lower()
    not_ready_ok = (merge_ready is False) and (status_val not in ("merge_ready", "ready", "merged"))
    checks.append((
        "not-merge-ready",
        not_ready_ok,
        f"merge_ready={merge_ready!r}, status={status_val!r}",
    ))

    raw_blockers = action.get("blockers")
    blocker_items: list[str] = []
    if isinstance(raw_blockers, list):
        blocker_items = [_serialize_item(b).lower() for b in raw_blockers]
    elif isinstance(raw_blockers, dict):
        blocker_items = [f"{k}: {_serialize_item(v)}".lower() for k, v in raw_blockers.items()]

    has_ci_blocker = any(
        "unit-tests" in item and any(tok in item for tok in ("fail", "ci", "check", "error", "red"))
        for item in blocker_items
    ) or (
        "unit-tests" in action_raw.lower()
        and isinstance(action.get("failing_checks"), list)
        and len(action["failing_checks"]) >= 1
    )
    checks.append((
        "blocker-ci-unit-tests",
        has_ci_blocker,
        "identified failing unit-tests check" if has_ci_blocker else "missing failing unit-tests blocker",
    ))

    has_thread_blocker = any(
        ("src/auth.py" in item and ("18" in item or "rt_42_1" in item or "thread" in item or "review" in item))
        for item in blocker_items
    ) or (
        "src/auth.py" in action_raw.lower()
        and isinstance(action.get("unresolved_threads"), list)
        and len(action["unresolved_threads"]) >= 1
    )
    checks.append((
        "blocker-review-thread",
        has_thread_blocker,
        "identified unresolved src/auth.py:18 review thread" if has_thread_blocker else "missing unresolved src/auth.py:18 thread blocker",
    ))

    rem_field = action.get("remediation") or action.get("next_steps") or action.get("actions")
    rem_text = _serialize_item(rem_field).lower() if rem_field is not None else ""
    if not rem_text and isinstance(raw_blockers, list):
        rem_text = " ".join(
            _serialize_item(b.get("remediation") or b.get("action") or "").lower()
            for b in raw_blockers
            if isinstance(b, dict)
        )
    rem_ok = (
        len(rem_text.strip()) >= 25
        and any(tok in rem_text for tok in ("unit-tests", "test", "ci", "fix"))
        and any(tok in rem_text for tok in ("thread", "review", "auth.py", "reply", "resolve"))
    )
    checks.append((
        "remediation-specified",
        rem_ok,
        "remediation covers both CI failure and review thread" if rem_ok else f"incomplete remediation: {rem_text[:120]!r}",
    ))

    sec_hits = _eval_kit.check_no_secrets([action_raw, final_text])
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks([action_raw, final_text])
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
