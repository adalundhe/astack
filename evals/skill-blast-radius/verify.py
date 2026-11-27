#!/usr/bin/env python3
"""Objective post-run verifier for skill-blast-radius."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


def _collect_report(ws: Path) -> str:
    parts: list[str] = []
    md = ws / "program" / "BLAST_RADIUS.md"
    if md.is_file():
        parts.append(md.read_text(encoding="utf-8", errors="replace").strip())
    ft = _eval_kit.final_text_from_env().strip()
    if ft:
        parts.append(ft)
    return "\n\n".join(p for p in parts if p)


def _cited_lines(text: str, filename: str) -> list[int]:
    pattern = re.compile(rf"{re.escape(filename)}:(\d+)")
    return [int(m.group(1)) for m in pattern.finditer(text)]


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("repo-exists", False, f"missing repo directory: {repo}"))
        return _eval_kit.report_and_exit(checks)

    ok_clean, msg_clean = _eval_kit.check_git_clean(repo)
    checks.append(("repo-clean", ok_clean, msg_clean))

    report = _collect_report(ws)
    low = report.lower()
    checks.append((
        "report-present",
        len(report) >= 200,
        f"collected {len(report)} chars across program/BLAST_RADIUS.md and final_text"
        if len(report) >= 200
        else "missing substantive blast-radius report in program/BLAST_RADIUS.md or final_text",
    ))

    # Exact file:line citations for all 3 indirect callers (within actual file line ranges)
    inv_lines = _cited_lines(report, "invoices.py")
    exp_lines = _cited_lines(report, "exports.py")
    wh_lines = _cited_lines(report, "webhooks.py")

    inv_ok = any(4 <= ln <= 15 for ln in inv_lines)
    exp_ok = any(4 <= ln <= 12 for ln in exp_lines)
    wh_ok = any(6 <= ln <= 25 for ln in wh_lines)
    checks.append((
        "all-three-indirect-callers-cited",
        inv_ok and exp_ok and wh_ok,
        f"invoices.py lines={inv_lines} (ok={inv_ok}), exports.py lines={exp_lines} (ok={exp_ok}), webhooks.py lines={wh_lines} (ok={wh_ok})",
    ))

    # Concrete indirect mechanisms & failure modes
    has_alias = "compute_order_total" in low or "alias" in low
    has_two_hop = "quote_amount" in low or "delegate" in low or "wrapper" in low
    has_dynamic = any(tok in low for tok in ("getattr", "registry", "calculator_registry", "dynamic"))
    checks.append((
        "indirect-mechanisms-identified",
        has_alias and has_two_hop and has_dynamic,
        f"aliased_import={has_alias}, two_hop_quote_amount={has_two_hop}, dynamic_registry={has_dynamic}",
    ))

    has_type_error = "typeerror" in low or ("dict" in low and "int" in low)
    has_ops_or_schema = (
        ("+=" in report or "add" in low or "sum" in low)
        and ("/" in report or "div" in low or "format" in low)
        and (">=" in report or "compar" in low or "amount_cents" in low or "wire" in low or "json" in low)
    )
    checks.append((
        "concrete-failure-modes",
        has_type_error and has_ops_or_schema,
        f"type_mismatch={has_type_error}, concrete_ops_or_schema={has_ops_or_schema}",
    ))

    challenges_assumption = (
        ("assumption" in low or "grep" in low)
        and any(tok in low for tok in ("false", "unproven", "refuted", "broken", "fails", "invalid", "unsafe", "breaks"))
    )
    checks.append((
        "core-safety-assumption-checked",
        challenges_assumption,
        "explicitly challenged the grep/direct-caller safety assumption"
        if challenges_assumption
        else "report did not explicitly evaluate/refute the core safety assumption",
    ))

    sec_hits = _eval_kit.check_no_secrets([report])
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks([report])
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
