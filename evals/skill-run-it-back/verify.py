#!/usr/bin/env python3
"""Executable verifier for `skill-run-it-back`."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


def _collect_alignment(ws: Path) -> str:
    parts: list[str] = []
    final_text = _eval_kit.final_text_from_env().strip()
    if final_text:
        parts.append(final_text)
    align = ws / "program" / "ALIGNMENT.md"
    if align.is_file():
        parts.append(align.read_text(encoding="utf-8", errors="replace").strip())
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

    text = _collect_alignment(ws)
    low = text.lower()
    checks.append((
        "alignment-present",
        bool(text.strip()),
        f"collected {len(text)} char(s)" if text.strip() else "no restatement in final_text or program/ALIGNMENT.md",
    ))

    has_goal = "goal" in low and "csv" in low and "active" in low and "invoice" in low
    checks.append((
        "restates-goal-active-invoice-csv",
        has_goal,
        "states goal for CSV export of active invoices"
        if has_goal
        else "missing explicit Goal covering CSV export of active invoices",
    ))

    has_problem_and_assumptions = ("problem" in low) and ("assumption" in low)
    checks.append((
        "states-problem-and-assumptions",
        has_problem_and_assumptions,
        f"problem={'problem' in low}, assumptions={'assumption' in low}",
    ))

    has_out_of_scope_heading = bool(re.search(r"\b(out\s+of\s+scope|non[- ]goals?|exclusions?)\b", low))
    excludes_pdf = "pdf" in low
    excludes_db_mig = bool(re.search(r"\b(db|database|schema)\s+migration|\bmigration\b", low))
    checks.append((
        "explicit-out-of-scope-boundaries",
        has_out_of_scope_heading and excludes_pdf and excludes_db_mig,
        f"section={has_out_of_scope_heading}, names_pdf={excludes_pdf}, names_db_migration={excludes_db_mig}",
    ))

    has_done_when = bool(re.search(r"\bdone\s+when\b", low))
    has_executable_check = bool(
        re.search(r"(`[^`]+`|python3?\b|unittest\b|exit\s*0|invoice_id,customer,amount_cents)", low)
    )
    checks.append((
        "executable-done-when-check",
        has_done_when and has_executable_check,
        f"done_when={has_done_when}, executable_check={has_executable_check}",
    ))

    sec_hits = _eval_kit.check_no_secrets([text])
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks([text])
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
