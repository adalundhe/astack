#!/usr/bin/env python3
"""Executable verifier for `skill-research-this`."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

_ASTACK_TOOLS = Path(__file__).resolve().parents[2] / "bin" / "astack-tools"
_DRIFTED_BANDS_RE = re.compile(r"\b(?:55\s*[-–]\s*69|30\s*[-–]\s*54)\b")
_GRADE_SCORE_PATTERNS = (
    re.compile(r"\bGrade\s*([ABCDF])\s*\(\s*(\d{1,3})\s*(?:/\s*100)?\s*\)", re.I),
    re.compile(r"\b([ABCDF])\s*\(\s*(\d{1,3})\s*(?:/\s*100)?\s*\)", re.I),
    re.compile(r"\bGrade\s*[:\-]?\s*([ABCDF])\b[^\n]{0,30}\bscore\s*[:=]?\s*(\d{1,3})\b", re.I),
    re.compile(r"\bscore\s*[:=]?\s*(\d{1,3})\b[^\n]{0,30}\bGrade\s*[:\-]?\s*([ABCDF])\b", re.I),
)


def _canonical_grade(score: int) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 50:
        return "C"
    if score >= 30:
        return "D"
    return "F"


def _extract_grade_score_pairs(text: str) -> list[tuple[str, int]]:
    pairs: list[tuple[str, int]] = []
    for idx, rx in enumerate(_GRADE_SCORE_PATTERNS):
        for m in rx.finditer(text):
            if idx == 3:
                score_val, grade_val = int(m.group(1)), m.group(2).upper()
            else:
                grade_val, score_val = m.group(1).upper(), int(m.group(2))
            if 0 <= score_val <= 100:
                pairs.append((grade_val, score_val))
    return pairs


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    astack_home = _eval_kit.astack_home_from_env(ws).resolve()
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("repo-exists", False, f"missing repo directory: {repo}"))
        return _eval_kit.report_and_exit(checks)

    clean_ok, clean_detail = _eval_kit.check_git_clean(repo)
    checks.append(("repo-git-clean", clean_ok, clean_detail))

    env = {**os.environ, "ASTACK_HOME": str(astack_home), "PYTHONDONTWRITEBYTECODE": "1"}
    res_proc = subprocess.run(
        [sys.executable, "-B", str(_ASTACK_TOOLS), "research", "list", "--project", "proto-check", "--json"],
        cwd=ws,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    res_entries: list[dict[str, object]] = []
    if res_proc.returncode == 0:
        try:
            payload = json.loads(res_proc.stdout)
            raw = payload.get("research")
            if isinstance(raw, list):
                res_entries = raw
        except json.JSONDecodeError:
            res_entries = []

    research_dir = astack_home / "proto-check" / "research"
    research_texts = [
        p.read_text(encoding="utf-8", errors="replace")
        for p in (sorted(research_dir.rglob("*")) if research_dir.is_dir() else [])
        if p.is_file() and not p.name.startswith(".")
    ]
    joined_research = "\n".join(research_texts)
    combined = "\n".join([joined_research, final_text])

    saved_ok = res_proc.returncode == 0 and len(res_entries) >= 1 and len(joined_research.strip()) >= 150
    checks.append((
        "research-persisted",
        saved_ok,
        f"astack-tools research list returned {len(res_entries)} entry/entries"
        if saved_ok
        else f"rc={res_proc.returncode}, count={len(res_entries)}",
    ))

    low = joined_research.lower()
    resolves_v21 = (
        "2.1" in low
        and ("sha-256" in low or "sha256" in low)
        and "official-spec-v2.1.md" in low
        and "client.py" in low
        and "old-blog-2021.md" in low
        and bool(re.search(r"\b(outdated|stale|superseded|removed|counterclaim|legacy)\b", low))
    )
    checks.append((
        "resolves-contradiction-with-primary-sources",
        resolves_v21,
        "cites official-spec-v2.1.md and client.py over outdated old-blog-2021.md"
        if resolves_v21
        else "missing primary source citations (spec + client.py), v2.1/SHA-256 conclusion, or outdated blog flag",
    ))

    norm_research = _normalize(joined_research)
    quote_verified = (
        "must send header x proto version 2 1 and use sha 256 hmac signatures" in norm_research
        or "legacy md5 signatures and x proto version 1 0 were removed in v2 0" in norm_research
        or "hmac new signing key payload hashlib sha256" in norm_research
    )
    checks.append((
        "verified-primary-quote",
        quote_verified,
        "exact primary-source quote present in saved research"
        if quote_verified
        else "missing verified verbatim quote from official-spec-v2.1.md or repo/src/client.py",
    ))

    drifted = _DRIFTED_BANDS_RE.findall(combined)
    checks.append((
        "no-drifted-grade-bands",
        not drifted,
        "zero drifted 55-69 / 30-54 bands" if not drifted else f"forbidden legacy band(s) found: {drifted}",
    ))

    pairs = _extract_grade_score_pairs(joined_research)
    mismatches = [
        f"Grade {g} ({s}) != canonical {_canonical_grade(s)}"
        for g, s in pairs
        if _canonical_grade(s) != g
    ]
    grades_ok = len(pairs) >= 1 and not mismatches
    checks.append((
        "canonical-grade-score-consistency",
        grades_ok,
        f"verified {len(pairs)} canonical (grade, score) pair(s): {pairs}"
        if grades_ok
        else f"pairs={pairs}, mismatches={mismatches}",
    ))

    sec_hits = _eval_kit.check_no_secrets([joined_research, final_text])
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks([joined_research, final_text])
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
