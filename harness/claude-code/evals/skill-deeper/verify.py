#!/usr/bin/env python3
"""Objective post-run verifier for skill-deeper."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

REQUIRED_SECTION_PATTERNS = (
    ("deliverable", re.compile(r"(?im)^(?:#{1,4}\s+|\*\*|[-*]\s*\*\*)?deliverable\b")),
    ("done-when", re.compile(r"(?im)^(?:#{1,4}\s+|\*\*|[-*]\s*\*\*)?done[- ]when\b")),
    ("writable-paths", re.compile(r"(?im)^(?:#{1,4}\s+|\*\*|[-*]\s*\*\*)?writable\s+paths\b")),
    ("non-goals", re.compile(r"(?im)^(?:#{1,4}\s+|\*\*|[-*]\s*\*\*)?(?:non[- ]goals|out\s+of\s+scope)\b")),
    ("edge-cases", re.compile(r"(?im)^(?:#{1,4}\s+|\*\*|[-*]\s*\*\*)?(?:edge\s+cases|expert\s+bar|failure\s+modes)\b")),
)


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    brief_path = ws / "program" / "brief.md"
    final_text = _eval_kit.final_text_from_env()

    checks: list[tuple[str, bool, str]] = []

    ok_clean, msg_clean = _eval_kit.check_git_clean(repo)
    checks.append(("repo-clean", ok_clean, msg_clean))

    brief_text = brief_path.read_text(encoding="utf-8") if brief_path.is_file() else ""
    low = brief_text.lower()

    rewritten_ok = len(brief_text.strip()) >= 500 and brief_text.strip().lower() != "# task brief\n\nmake the cache better."
    checks.append((
        "brief-rewritten",
        rewritten_ok,
        f"program/brief.md rewritten ({len(brief_text.strip())} chars)"
        if rewritten_ok
        else f"program/brief.md still too short or unchanged ({len(brief_text.strip())} chars)",
    ))

    missing_sections = [name for name, rx in REQUIRED_SECTION_PATTERNS if not rx.search(brief_text)]
    checks.append((
        "required-sections",
        not missing_sections,
        "all required brief sections present (Deliverable, Done when, Writable paths, Non-goals, Edge cases)"
        if not missing_sections
        else f"missing required section(s): {', '.join(missing_sections)}",
    ))

    # Grounded in primary repo source: cites cache.py, test_cache.py, and the real bugs found in cache.py
    mentions_src = "src/cache.py" in low
    mentions_test = "test_cache.py" in low
    mentions_bound = "max_entries" in low or "size bound" in low or "capacity" in low
    mentions_eviction = ("lru" in low or "evict" in low) and ("popitem" in low or "lifo" in low or "oldest" in low or "recency" in low)
    mentions_clock = "monotonic" in low or "time.time" in low or "clock" in low
    grounded_ok = mentions_src and mentions_test and mentions_bound and mentions_eviction and mentions_clock
    checks.append((
        "grounded-in-repo-bugs",
        grounded_ok,
        "cites src/cache.py, tests/test_cache.py, max_entries bound, LRU/popitem eviction bug, and monotonic clock bug"
        if grounded_ok
        else (
            f"missing primary repo receipts (src={mentions_src}, test={mentions_test}, "
            f"bound={mentions_bound}, eviction={mentions_eviction}, clock={mentions_clock})"
        ),
    ))

    # Executable done-when command + external proof / domain method
    has_exec_cmd = "unittest" in low or "python3" in low or "pytest" in low
    has_method_or_proof = (
        ("ordereddict" in low or "monotonic" in low)
        and ("reference" in low or "differential" in low or "oracle" in low or "property" in low or "randomized" in low or "fake clock" in low or "injected clock" in low)
    )
    checks.append((
        "executable-done-when-and-proof",
        has_exec_cmd and has_method_or_proof,
        "includes executable test command, domain methods, and external/reference verification"
        if (has_exec_cmd and has_method_or_proof)
        else f"missing executable done-when or proof details (cmd={has_exec_cmd}, method_proof={has_method_or_proof})",
    ))

    sec = _eval_kit.check_no_secrets([brief_text, final_text])
    checks.append(("no-secrets", not sec, "; ".join(sec) if sec else "no secrets"))

    leaks = _eval_kit.check_no_internal_leaks([final_text])
    checks.append(("no-internal-leaks", not leaks, "; ".join(leaks) if leaks else "no internal leaks"))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
