#!/usr/bin/env python3
"""Executable verifier for `skill-rtfm`."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


def _ad007_commit_sha(repo: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "log", "--grep=AD-007", "--format=%H", "-n", "1"],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    final_text = _eval_kit.final_text_from_env()
    answer_file = ws / "program" / "ANSWER.md"
    answer_extra = answer_file.read_text(encoding="utf-8", errors="replace") if answer_file.is_file() else ""
    combined = "\n".join(part for part in (final_text, answer_extra) if part.strip())
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("repo-exists", False, f"missing repo directory: {repo}"))
        return _eval_kit.report_and_exit(checks)

    clean_ok, clean_detail = _eval_kit.check_git_clean(repo)
    checks.append(("repo-git-clean", clean_ok, clean_detail))

    full_sha = _ad007_commit_sha(repo)
    short7 = full_sha[:7]
    low = combined.lower()

    has_reason = (
        "429" in low
        and bool(re.search(r"\b(4th|fourth)\b", low))
        and "ban" in low
    )
    checks.append((
        "answers-settled-429-reason",
        has_reason,
        "explains upstream strict 429 ban on 4th attempt"
        if has_reason
        else "answer missing 429 / 4th attempt / ban rationale from AD-007",
    ))

    cites_doc = "docs/ad-007.md" in low or "ad-007.md" in low
    cites_sha = bool(short7) and short7.lower() in low
    checks.append((
        "cites-ad007-and-commit-sha",
        cites_doc and cites_sha,
        f"cites AD-007.md and commit {short7}"
        if (cites_doc and cites_sha)
        else f"cites_doc={cites_doc}, cites_sha({short7})={cites_sha}",
    ))

    deflected_to_author = bool(
        re.search(r"\b(?:yes[,!\s]+)?(?:you should|go|please)\s+ask\s+the\s+author\b", low)
    )
    checks.append((
        "does-not-deflect-to-author",
        bool(combined.strip()) and not deflected_to_author,
        "answers directly without deflecting to the author"
        if (bool(combined.strip()) and not deflected_to_author)
        else "empty answer or told user to ask the author",
    ))

    sec_hits = _eval_kit.check_no_secrets([combined])
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks([combined])
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
