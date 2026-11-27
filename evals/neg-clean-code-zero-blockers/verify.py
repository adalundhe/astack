#!/usr/bin/env python3
"""Objective post-run verifier for neg-clean-code-zero-blockers."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


def _collect_review_text(ws: Path, final_text: str) -> str:
    parts: list[str] = []
    if final_text.strip():
        parts.append(final_text)
    review_md = ws / "program" / "REVIEW.md"
    if review_md.is_file():
        parts.append(review_md.read_text(encoding="utf-8", errors="replace"))
    return "\n\n".join(parts)


def _check_clear_verdict_and_held(text: str) -> tuple[bool, str]:
    if not text.strip():
        return False, "empty review output (neither final_text nor program/REVIEW.md provided)"
    if re.search(r"\bVERDICT\s*:\s*BLOCKED\b", text, re.IGNORECASE):
        return False, "false-positive VERDICT: BLOCKED reported on clean code"
    if not re.search(r"\bVERDICT\s*:\s*CLEAR\b", text, re.IGNORECASE):
        return False, "missing VERDICT: CLEAR in review output"

    # Extract BLOCKING section if present and confirm it reports zero blockers
    m_block = re.search(
        r"(?:^|\n)\s*(?:#{1,4}\s*)?BLOCKING\s*:?(.*?)(?=(?:\n\s*(?:#{1,4}\s*)?(?:HELD|NON-BLOCKING|NOTES|SUMMARY|VERDICT)\b)|\Z)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if m_block:
        block_body = m_block.group(1).strip()
        if block_body and not re.fullmatch(r"(?:[-*]\s*)?(?:none|n/a|0|no\s+blocking\s+findings?)\.?", block_body, re.IGNORECASE):
            return False, f"BLOCKING section is non-empty: {block_body[:160]}"

    # Require concrete HELD checks citing real invariants from atomic_store.py
    has_held_heading = bool(re.search(r"(?:^|\n)\s*(?:#{1,4}\s*)?HELD\b", text, re.IGNORECASE))
    low = text.lower()
    invariant_hits = [
        tok
        for tok in ("fsync", "os.replace", "lock", "validation", "valueerror", "unittest", "test_atomic_store", "deepcopy", "temp")
        if tok in low
    ]
    if not has_held_heading or len(invariant_hits) < 2:
        return False, f"missing concrete HELD verification details (has_held={has_held_heading}, invariants={invariant_hits})"
    return True, f"VERDICT: CLEAR with zero blockers and verified HELD checks ({', '.join(invariant_hits[:4])})"


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    final_text = _eval_kit.final_text_from_env()
    review_text = _collect_review_text(ws, final_text)

    checks: list[tuple[str, bool, str]] = []
    checks.append(("repo-git-clean", *_eval_kit.check_git_clean(repo)))
    checks.append(("unittest", *_eval_kit.run_unittest(repo)))
    checks.append(("clear-verdict-and-held", *_check_clear_verdict_and_held(review_text)))

    sec = _eval_kit.check_no_secrets([review_text])
    checks.append(("no-secrets", not sec, "; ".join(sec) if sec else "no secrets"))

    leaks = _eval_kit.check_no_internal_leaks([review_text])
    checks.append(("no-internal-leaks", not leaks, "; ".join(leaks) if leaks else "no internal leaks"))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
