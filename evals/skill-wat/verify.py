#!/usr/bin/env python3
"""Executable verifier for `skill-wat`."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

_EXTRA_FORBIDDEN_JARGON = (
    "n1=2",
    "n2=2",
    "m=1",
    "lane-42",
    "wt-8841",
    "no-shared-writes",
    "a91c4ef",
)


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    final_text = _eval_kit.final_text_from_env().strip()
    summary_path = ws / "program" / "SUMMARY.md"
    summary_text = summary_path.read_text(encoding="utf-8", errors="replace").strip() if summary_path.is_file() else ""
    primary_out = summary_text or final_text
    all_outputs = [part for part in (summary_text, final_text) if part]
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("repo-exists", False, f"missing repo directory: {repo}"))
        return _eval_kit.report_and_exit(checks)

    clean_ok, clean_detail = _eval_kit.check_git_clean(repo)
    checks.append(("repo-git-clean", clean_ok, clean_detail))

    if not primary_out:
        checks.append(("rewrite-present", False, "neither program/SUMMARY.md nor final_text has content"))
        return _eval_kit.report_and_exit(checks)
    checks.append(("rewrite-present", True, f"rewrite length {len(primary_out)} chars"))

    head = primary_out[:350].lower()
    lede_first = (
        ("double-charge" in head or "double charge" in head or "duplicate charge" in head)
        and ("race condition" in head or "orders" in head)
    )
    checks.append((
        "losses-and-blocker-first",
        lede_first,
        "orders race condition / double-charge blocker leads in the opening 350 chars"
        if lede_first
        else f"blocker not at top of rewrite; opening preview: {head[:160]!r}",
    ))

    low = primary_out.lower()
    has_action = bool(
        re.search(r"\b(do not ship|block|hold|pause|add a|unique|constraint|row lock|lock|idempotency)\b", low)
    )
    preserves_facts = (
        "v2.4" in low
        and bool(re.search(r"\b3\b", low))
        and bool(re.search(r"\b12\b", low))
        and "180" in low
    )
    checks.append((
        "action-and-facts-preserved",
        has_action and preserves_facts,
        "concrete action and key staging numbers (v2.4, 3/12, 180ms) preserved"
        if (has_action and preserves_facts)
        else f"has_action={has_action}, preserves_facts={preserves_facts}",
    ))

    leak_hits = _eval_kit.check_no_internal_leaks(all_outputs)
    extra_hits = [
        tok for tok in _EXTRA_FORBIDDEN_JARGON
        if any(tok in txt.lower() for txt in all_outputs)
    ]
    all_leaks = [*leak_hits, *(f"forbidden jargon {t!r}" for t in extra_hits)]
    checks.append((
        "zero-internal-leaks",
        not all_leaks,
        "zero internal jargon leaked" if not all_leaks else "; ".join(all_leaks),
    ))

    sec_hits = _eval_kit.check_no_secrets(all_outputs)
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
