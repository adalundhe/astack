#!/usr/bin/env python3
"""Executable verifier for `skill-status`."""
from __future__ import annotations

import re
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


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    sha_path = ws / "program" / "base_sha.txt"
    status_path = ws / "program" / "STATUS.md"
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir() or not sha_path.is_file():
        checks.append(("workspace-intact", False, "missing repo or program/base_sha.txt"))
        return _eval_kit.report_and_exit(checks)

    base_sha = sha_path.read_text(encoding="utf-8").strip()

    clean_ok, clean_detail = _eval_kit.check_git_clean(repo)
    checks.append(("git-clean", clean_ok, clean_detail))

    head_sha = _git(repo, "rev-parse", "HEAD")
    checks.append((
        "repo-head-unchanged",
        head_sha == base_sha,
        f"HEAD={head_sha[:7]} unchanged" if head_sha == base_sha else f"HEAD changed to {head_sha}",
    ))

    file_text = status_path.read_text(encoding="utf-8") if status_path.is_file() else ""
    combined = "\n".join(part for part in (final_text, file_text) if part.strip()).strip()
    checks.append(("report-present", len(combined) >= 40, f"{len(combined)} chars"))

    low = combined.lower()

    core_ok = ("lane/core" in low) and any(tok in low for tok in ("closed", "merged"))
    checks.append((
        "lane-core-merged",
        core_ok,
        "lane/core reported as closed/merged" if core_ok else "missing lane/core merged/closed status",
    ))

    api_ok = ("lane/api" in low) and any(
        tok in low for tok in ("open", "active", "running", "healthy", "on track", "in ")
    )
    api_not_overdue = not bool(
        re.search(r"lane/api[^\n]{0,30}\b(overdue|past by|past limit|past wind-down)\b", low)
    )
    checks.append((
        "lane-api-healthy-active",
        api_ok and api_not_overdue,
        "lane/api reported active/healthy"
        if (api_ok and api_not_overdue)
        else f"api_present_active={api_ok}, api_not_falsely_overdue={api_not_overdue}",
    ))

    index_present = "lane/index" in low
    index_overdue = bool(
        re.search(r"lane/index[\s\S]{0,160}\b(overdue|past by|past limit|past wind-down|past its|exceeded)\b", low)
        or re.search(r"\b(overdue|past by|past limit|past wind-down)\b[\s\S]{0,120}lane/index", low)
    )
    checks.append((
        "lane-index-flagged-overdue",
        index_present and index_overdue,
        "lane/index flagged as overdue/past wind-down"
        if (index_present and index_overdue)
        else "lane/index not clearly flagged as overdue",
    ))

    counts_ok = (
        ("lane/core" in low and "lane/api" in low and "lane/index" in low)
        and (
            bool(re.search(r"\b2\b.{0,25}\b(active|running|open)\b", low))
            or bool(re.search(r"\b(active|running|open)\b.{0,25}\b2\b", low))
            or ("lane/api: open" in low and "lane/index: open" in low and "lane/core: closed" in low)
        )
    )
    checks.append((
        "exact-lane-counts-and-states",
        counts_ok,
        "exact lane counts/states reported" if counts_ok else "missing explicit active/closed lane counts or verbatim lane states",
    ))

    sec_hits = _eval_kit.check_no_secrets([combined])
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks([combined])
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
