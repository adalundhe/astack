#!/usr/bin/env python3
"""Executable verifier for `skill-whatsup`."""
from __future__ import annotations

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
    sha_path = ws / "program" / "merged_sha.txt"
    catchup_path = ws / "program" / "CATCHUP.md"
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir() or not sha_path.is_file():
        checks.append(("workspace-intact", False, "missing repo or program/merged_sha.txt"))
        return _eval_kit.report_and_exit(checks)

    merged_sha = sha_path.read_text(encoding="utf-8").strip()
    merged_short = merged_sha[:7]

    clean_ok, clean_detail = _eval_kit.check_git_clean(repo)
    checks.append(("git-clean", clean_ok, clean_detail))

    head_sha = _git(repo, "rev-parse", "HEAD")
    checks.append((
        "repo-head-unchanged",
        head_sha == merged_sha,
        f"HEAD={head_sha[:7]} unchanged" if head_sha == merged_sha else f"HEAD changed to {head_sha}",
    ))

    file_text = catchup_path.read_text(encoding="utf-8") if catchup_path.is_file() else ""
    combined = "\n".join(part for part in (final_text, file_text) if part.strip()).strip()
    checks.append(("summary-present", len(combined) >= 40, f"{len(combined)} chars"))

    low = combined.lower()

    fact1 = (
        ("lane/parser" in low or "parser" in low)
        and (merged_short in combined)
        and any(tok in low for tok in ("merg", "land", "ship", "closed"))
    )
    checks.append((
        "fact-parser-merged-sha",
        fact1,
        f"lane/parser merged at {merged_short} reported" if fact1 else f"missing lane/parser merged SHA {merged_short}",
    ))

    fact2 = (
        ("lane/cache" in low or "cache" in low)
        and any(tok in low for tok in ("block", "wait"))
        and any(tok in low for tok in ("schema", "cache_ttl_seconds"))
    )
    checks.append((
        "fact-cache-blocked-schema-key",
        fact2,
        "lane/cache blocked on missing schema key reported" if fact2 else "missing lane/cache missing schema key blocker",
    ))

    fact3 = ("sqlite" in low) and ("wal" in low)
    checks.append((
        "fact-decided-sqlite-wal",
        fact3,
        "SQLite WAL mode decision reported" if fact3 else "missing settled SQLite WAL mode decision",
    ))

    sec_hits = _eval_kit.check_no_secrets([combined])
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks([combined])
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
