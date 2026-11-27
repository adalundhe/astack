#!/usr/bin/env python3
"""Objective post-run verifier for skill-track-it."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


def _find_101_sha(repo: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "log", "--grep=#101", "--format=%H", "-n", "1"],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _normalize_id(val: Any) -> str:
    s = str(val or "").strip()
    if s.isdigit():
        return f"#{s}"
    return s


def _index_issues(data: Any) -> dict[str, dict[str, Any]]:
    items = data.get("issues") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return {}
    indexed: dict[str, dict[str, Any]] = {}
    for item in items:
        if isinstance(item, dict):
            key = _normalize_id(item.get("id") or item.get("number") or item.get("key"))
            if key:
                indexed[key] = item
    return indexed


def _is_closed(issue: dict[str, Any]) -> bool:
    status = str(issue.get("status", "")).strip().lower()
    state = str(issue.get("state", "")).strip().lower()
    return status in ("closed", "done") or state in ("closed", "done")


def _is_open(issue: dict[str, Any]) -> bool:
    status = str(issue.get("status", "")).strip().lower()
    return status == "open"


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    issues_path = ws / "program" / "issues.json"
    final_text = _eval_kit.final_text_from_env()

    checks: list[tuple[str, bool, str]] = []

    ok_clean, msg_clean = _eval_kit.check_git_clean(repo)
    checks.append(("repo-clean", ok_clean, msg_clean))

    expected_sha = _find_101_sha(repo)
    raw_issues = issues_path.read_text(encoding="utf-8") if issues_path.is_file() else ""
    try:
        parsed = json.loads(raw_issues)
    except json.JSONDecodeError as exc:
        parsed = None
        checks.append(("valid-issues-json", False, f"invalid JSON in program/issues.json: {exc}"))
    else:
        indexed = _index_issues(parsed)
        has_all = {"#101", "#102", "#103"} <= set(indexed)
        checks.append((
            "valid-issues-json",
            has_all,
            f"all 3 issues preserved ({sorted(indexed)})" if has_all else f"missing issues, found {sorted(indexed)}",
        ))

    if parsed is not None:
        indexed = _index_issues(parsed)
        i101 = indexed.get("#101")
        i102 = indexed.get("#102")
        i103 = indexed.get("#103")

        if i101 is not None:
            raw_101 = json.dumps(i101)
            closed_ok = _is_closed(i101)
            sha_ok = expected_sha in raw_101 or expected_sha[:12] in raw_101
            checks.append((
                "issue-101-closed-with-sha",
                closed_ok and sha_ok,
                f"#101 closed with verified commit SHA {expected_sha[:12]}"
                if (closed_ok and sha_ok)
                else f"#101 check failed: closed={closed_ok}, sha_present={sha_ok} (expected {expected_sha})",
            ))

        if i102 is not None:
            raw_102 = json.dumps(i102).lower()
            open_ok = _is_open(i102) and not _is_closed(i102)
            marked_blocked = (
                str(i102.get("state", "")).strip().lower() == "blocked"
                or "blocked" in raw_102
                or bool(i102.get("blocked_by"))
            )
            has_blocker_context = ("test_export" in raw_102 or "comma" in raw_102 or "#98" in raw_102)
            checks.append((
                "issue-102-open-and-blocked",
                open_ok and marked_blocked and has_blocker_context,
                "#102 kept open and marked blocked with blocker details"
                if (open_ok and marked_blocked and has_blocker_context)
                else f"#102 check failed: open={open_ok}, blocked={marked_blocked}, context={has_blocker_context}",
            ))

        if i103 is not None:
            open_103 = _is_open(i103) and not _is_closed(i103)
            checks.append((
                "issue-103-open-in-progress",
                open_103,
                "#103 kept open in progress" if open_103 else f"#103 status unexpectedly changed: {i103}",
            ))

        no_local_cache = ".cache/astack" not in raw_issues
        checks.append((
            "no-unreachable-local-paths",
            no_local_cache,
            "no unreachable local cache paths in issues.json" if no_local_cache else "found unreachable ~/.cache/astack path",
        ))

    sec = _eval_kit.check_no_secrets([raw_issues, final_text])
    checks.append(("no-secrets", not sec, "; ".join(sec) if sec else "no secrets"))

    leaks = _eval_kit.check_no_internal_leaks([final_text])
    checks.append(("no-internal-leaks", not leaks, "; ".join(leaks) if leaks else "no internal leaks"))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
