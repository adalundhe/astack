#!/usr/bin/env python3
"""Executable verifier for `skill-checkpoint`."""
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
    cp_path = ws / "program" / "CHECKPOINT.md"
    sha_path = ws / "program" / "step1_sha.txt"
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir() or not sha_path.is_file():
        checks.append(("workspace-intact", False, "missing repo or program/step1_sha.txt"))
        return _eval_kit.report_and_exit(checks)

    expected_sha = sha_path.read_text(encoding="utf-8").strip()
    short_sha = expected_sha[:7]

    branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    checks.append(("branch-lane-billing", branch == "lane/billing", f"branch={branch}"))

    head_sha = _git(repo, "rev-parse", "HEAD")
    checks.append((
        "head-unchanged",
        head_sha == expected_sha,
        f"HEAD={head_sha[:7]} matches step 1 {short_sha}" if head_sha == expected_sha else f"HEAD moved to {head_sha}",
    ))

    clean_ok, clean_detail = _eval_kit.check_git_clean(repo)
    checks.append(("git-clean", clean_ok, clean_detail))

    ut_ok, ut_detail = _eval_kit.run_unittest(repo)
    checks.append(("unittest", ut_ok, ut_detail))

    if not cp_path.is_file():
        checks.append(("checkpoint-exists", False, "missing program/CHECKPOINT.md"))
        return _eval_kit.report_and_exit(checks)

    cp_text = cp_path.read_text(encoding="utf-8")
    low = cp_text.lower()
    checks.append(("checkpoint-exists", len(cp_text.strip()) >= 60, f"{len(cp_text.strip())} chars"))

    checks.append((
        "captures-branch",
        "lane/billing" in cp_text,
        "branch lane/billing present" if "lane/billing" in cp_text else "missing branch name lane/billing",
    ))

    has_sha = (expected_sha in cp_text) or (short_sha in cp_text)
    checks.append((
        "captures-commit-sha",
        has_sha,
        f"commit SHA ({short_sha}) present" if has_sha else f"missing commit SHA {expected_sha} / {short_sha}",
    ))

    has_step1 = ("add_line_item" in cp_text or "subtotal" in low) and any(
        tok in low for tok in ("step 1", "completed", "done", "committed")
    )
    checks.append((
        "captures-completed-step1",
        has_step1,
        "step 1 completed work recorded" if has_step1 else "missing completed step 1 summary",
    ))

    has_step2 = ("apply_discount" in cp_text) and any(
        tok in low for tok in ("step 2", "remaining", "next", "pending", "todo")
    )
    checks.append((
        "captures-remaining-step2",
        has_step2,
        "step 2 remaining work recorded" if has_step2 else "missing remaining step 2 (`apply_discount`)",
    ))

    has_verify_cmd = ("unittest" in low) and ("discover" in low) and ("tests" in low)
    checks.append((
        "captures-verification-command",
        has_verify_cmd,
        "exact unittest discover command present" if has_verify_cmd else "missing exact unittest verification command",
    ))

    sec_hits = _eval_kit.check_no_secrets([cp_text, final_text])
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks([cp_text, final_text])
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
