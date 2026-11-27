#!/usr/bin/env python3
"""Objective post-run verifier for skill-lookup."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


def _collect_report(ws: Path) -> str:
    parts: list[str] = []
    ctx = ws / "program" / "CONTEXT.md"
    if ctx.is_file():
        parts.append(ctx.read_text(encoding="utf-8", errors="replace").strip())
    ft = _eval_kit.final_text_from_env().strip()
    if ft:
        parts.append(ft)
    return "\n\n".join(p for p in parts if p)


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
        "synthesis-present",
        len(report) >= 200,
        f"collected {len(report)} chars across program/CONTEXT.md and final_text"
        if len(report) >= 200
        else "missing substantive lookup synthesis in program/CONTEXT.md or final_text",
    ))

    cites_active_lesson = (
        "tax-rounding" in low
        and ("per-line" in low or "per line" in low)
        and ("5000" in report or "half-up" in low or "half up" in low)
        and "ledger-sync" in low
    )
    checks.append((
        "cites-active-lesson-tax-rounding",
        cites_active_lesson,
        "cited active tax-rounding lesson (per-line half-up integer math + ledger-sync)"
        if cites_active_lesson
        else "missing active tax-rounding lesson details (tax-rounding, per-line, half-up/5000, ledger-sync)",
    ))

    cites_ad1 = (
        bool(re.search(r"\bad[_-]?1\b", low))
        and ("cent" in low or "minor-unit" in low or "minor unit" in low)
        and ("integer" in low or "no float" in low or "float" in low)
    )
    checks.append((
        "cites-accepted-ad1",
        cites_ad1,
        "cited accepted AD_1 integer minor-unit constraint"
        if cites_ad1
        else "missing AD_1 / integer minor-unit cents constraint",
    ))

    cites_contract = (
        ("api.md" in low or "/v2/invoices" in low)
        and "idempotency-key" in low
        and ("tax_rate_bps" in low or "unit_price_cents" in low)
        and "usd" in low
    )
    checks.append((
        "cites-contract-doc",
        cites_contract,
        "cited docs/contracts/api.md (POST /v2/invoices, Idempotency-Key, integer fields, USD default)"
        if cites_contract
        else "missing docs/contracts/api.md contract details",
    ))

    mentions_old_vat = "old-vat" in low or "legacy_vat_float" in low
    marks_superseded = bool(
        re.search(r"\b(superseded|ignore[ds]?|retired|obsolete|do\s+not\s+use|deprecated|stale)\b", low)
    )
    recommends_legacy = bool(
        re.search(r"\b(use|call|adopt|apply)\s+`?legacy_vat_float`?\b", low)
        and not re.search(r"\b(do\s+not|never|don't|avoid|not)\s+(?:use|call|adopt|apply)\s+`?legacy_vat_float`?\b", low)
    )
    checks.append((
        "superseded-lesson-flagged-and-ignored",
        mentions_old_vat and marks_superseded and not recommends_legacy,
        f"mentions_old_vat={mentions_old_vat}, marks_superseded={marks_superseded}, recommends_legacy={recommends_legacy}",
    ))

    verified_live_code = "billing.py" in low
    checks.append((
        "verified-against-live-code",
        verified_live_code,
        "verified saved memories against live repo/src/billing.py"
        if verified_live_code
        else "did not cite verification against live repo/src/billing.py",
    ))

    sec_hits = _eval_kit.check_no_secrets([report])
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks([report])
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
