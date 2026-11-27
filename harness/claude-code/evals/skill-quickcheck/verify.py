#!/usr/bin/env python3
"""Objective post-run verifier for skill-quickcheck."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


def _blocking_section(text: str) -> str:
    match = re.search(
        r"(?im)^(?:#+\s*)?BLOCKING(?:\s*\(P0[–-]P2\))?\s*:?\s*$(.*?)(?=^(?:#+\s*)?(?:SUGGESTIONS|NITS|UNPROVEN|CONFIRMED|HELD|COULD NOT TEST|NOT CHECKED|NON-BLOCKING)\b|\Z)",
        text,
        re.S,
    )
    return match.group(1).strip() if match else ""


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("repo-exists", False, f"missing repo directory: {repo}"))
        return _eval_kit.report_and_exit(checks)

    ok_clean, msg_clean = _eval_kit.check_git_clean(repo)
    checks.append(("repo-clean", ok_clean, msg_clean))

    report_path = ws / "program" / "QUICKCHECK.md"
    if not report_path.is_file():
        checks.append(("report-exists", False, "missing program/QUICKCHECK.md"))
        return _eval_kit.report_and_exit(checks)

    text = report_path.read_text(encoding="utf-8")
    ok_verdict = bool(re.search(r"(?im)^VERDICT:\s*BLOCKED\b", text))
    checks.append(("verdict-blocked", ok_verdict, "expected VERDICT: BLOCKED in program/QUICKCHECK.md"))

    blocking = _blocking_section(text)
    low_blocking = blocking.lower()
    catches_real_bug = (
        bool(blocking)
        and "cache.py" in low_blocking
        and any(k in low_blocking for k in ("duplicate", "evict", "existing key", "_order", "overwrite"))
    )
    checks.append(("catches-real-blocker", catches_real_bug, f"blocking section={blocking[:240]!r}"))

    noisy_hits = [
        label
        for label, pat in (
            ("lru", r"\blru\b"),
            ("locking", r"\b(lock|mutex|thread[- ]?safe)\b"),
            ("data_dir", r"\bdata_dir\b|\./var/data"),
        )
        if re.search(pat, blocking, re.I)
    ]
    checks.append(("no-context-blind-blockers", not noisy_hits, f"noisy flags in BLOCKING: {noisy_hits}"))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
