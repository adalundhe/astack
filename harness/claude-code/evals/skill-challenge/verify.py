#!/usr/bin/env python3
"""Executable verifier for `skill-challenge`."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


def _collect_challenge(ws: Path) -> str:
    parts: list[str] = []
    final_text = _eval_kit.final_text_from_env().strip()
    if final_text:
        parts.append(final_text)
    challenge_doc = ws / "program" / "CHALLENGE.md"
    if challenge_doc.is_file():
        parts.append(challenge_doc.read_text(encoding="utf-8", errors="replace").strip())
    return "\n\n".join(p for p in parts if p)


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("repo-exists", False, f"missing repo directory: {repo}"))
        return _eval_kit.report_and_exit(checks)

    clean_ok, clean_detail = _eval_kit.check_git_clean(repo)
    checks.append(("repo-untouched", clean_ok, clean_detail))

    text = _collect_challenge(ws)
    low = text.lower()
    checks.append((
        "challenge-present",
        bool(text.strip()),
        f"collected {len(text)} char(s)" if text.strip() else "no challenge in final_text or program/CHALLENGE.md",
    ))

    cites_search = "src/search.py" in low or "search.py" in low
    checks.append(("cites-search-py", cites_search, f"cites src/search.py={cites_search}"))

    falsifies_io = bool(
        re.search(r"\b(no|zero|without|never|not)\b.{0,45}\b(disk|file(?:system)?|i/?o|open\()", low, re.S)
        or re.search(r"\b(disk|file(?:system)?|i/?o)\b.{0,45}\b(zero|none|absent|does not|doesn't|no\b)", low, re.S)
    )
    mentions_lru = "lru" in low or "file cache" in low
    checks.append((
        "falsifies-disk-io-hypothesis",
        falsifies_io and mentions_lru,
        f"falsifies_disk_io={falsifies_io}, addresses_lru_cache={mentions_lru}",
    ))

    names_quadratic = bool(
        re.search(r"(o\s*\(\s*n\s*(?:\^2|\*\*2|²|\*\s*m|\*\s*q|×\s*m)\s*\)|quadratic|nested\s+loop|in-memory)", low)
    ) and bool(re.search(r"(o\s*\(\s*n\s*(?:\^2|\*\*2|²|\*\s*m|\*\s*q|×\s*m)\s*\)|quadratic|nested\s+loop)", low))
    checks.append((
        "identifies-quadratic-in-memory-bottleneck",
        names_quadratic,
        "identifies O(n^2)/nested-loop in-memory scan"
        if names_quadratic
        else "missing explicit identification of O(n^2)/quadratic nested-loop in-memory bottleneck",
    ))

    has_alternative = bool(
        re.search(r"\b(dict|hash\s*(?:map|table|index)|inverted\s+index|set\b|o\s*\(\s*1\s*\)|o\s*\(\s*n\s*\+\s*m\s*\)|seen\s+set|pre-?index)", low)
    )
    checks.append((
        "proposes-concrete-alternative",
        has_alternative,
        "proposes hash/dict/set index alternative" if has_alternative else "missing concrete indexed/hash alternative",
    ))

    has_verdict = bool(re.search(r"\b(rejected|revised|decided:)\b", low))
    checks.append((
        "explicit-verdict",
        has_verdict,
        "includes explicit Rejected/Revised/decided verdict" if has_verdict else "missing explicit verdict (Rejected/Revised/decided:)",
    ))

    sec_hits = _eval_kit.check_no_secrets([text])
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks([text])
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
