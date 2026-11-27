#!/usr/bin/env python3
"""Objective post-run verifier for skill-plan-it."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


def _find_grilling_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(p for p in root.rglob("GRILLING.md") if p.is_file())


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    astack_home = _eval_kit.astack_home_from_env(ws)
    final_text = _eval_kit.final_text_from_env()

    checks: list[tuple[str, bool, str]] = []

    ok_clean, msg_clean = _eval_kit.check_git_clean(repo)
    checks.append(("repo-clean", ok_clean, msg_clean))

    repo_grilling = _find_grilling_files(repo)
    checks.append((
        "no-grilling-in-repo",
        not repo_grilling,
        "no GRILLING.md inside repo" if not repo_grilling else f"GRILLING.md written inside repo: {repo_grilling}",
    ))

    arch_grilling = astack_home / "billing" / "architecture" / "GRILLING.md"
    grilling_files = _find_grilling_files(astack_home)
    grilling_text = "\n".join(p.read_text(encoding="utf-8") for p in grilling_files)
    combined = "\n".join(part for part in (final_text, grilling_text) if part).strip()
    low = combined.lower()

    has_output = len(combined) >= 200
    checks.append((
        "substantive-output",
        has_output,
        f"combined output length {len(combined)} chars" if has_output else "no planning response or GRILLING.md produced",
    ))

    # Surface spec-vs-code contradiction: docs/spec.md says 72h vs src/billing.py says 24h
    mentions_spec = "spec.md" in low
    mentions_code = "billing.py" in low
    mentions_72 = bool(re.search(r"\b72\b", combined))
    mentions_24 = bool(re.search(r"\b24\b", combined))
    contradiction_ok = mentions_spec and mentions_code and mentions_72 and mentions_24
    checks.append((
        "spec-code-contradiction",
        contradiction_ok,
        "surfaced 72h (docs/spec.md) vs 24h (src/billing.py) contradiction"
        if contradiction_ok
        else f"missing contradiction receipts (spec.md={mentions_spec}, billing.py={mentions_code}, 72={mentions_72}, 24={mentions_24})",
    ))

    # Surface request conflicts: 500ms synchronous vs 10s gateway retries, or unlimited vs 24h/no-duplicate
    mentions_latency_conflict = (
        ("500" in low and ("10" in low or "30" in low or "timeout" in low or "sync" in low))
        and ("async" in low or "queue" in low or "background" in low or "worker" in low)
    )
    mentions_retry_conflict = (
        ("unlimited" in low or "duplicate" in low or "idempoten" in low)
        and ("24" in low or "cutoff" in low or "window" in low)
    )
    conflicts_ok = mentions_latency_conflict and mentions_retry_conflict
    checks.append((
        "request-conflicts-surfaced",
        conflicts_ok,
        "surfaced sync/500ms and unlimited/idempotency conflicts"
        if conflicts_ok
        else f"missing conflict analysis (latency={mentions_latency_conflict}, retry={mentions_retry_conflict})",
    ))

    # Focused decision with trade-offs and a clear recommendation
    has_options = bool(re.search(r"\b(option\s+[ab12]|approach\s+[ab12]|trade-?off|vs\.?)\b", low))
    has_recommendation = bool(re.search(r"\b(recommend|pick|prefer|propose)\b", low))
    decision_ok = has_options and has_recommendation
    checks.append((
        "focused-decision-and-pick",
        decision_ok,
        "presented options/trade-offs and a clear recommendation"
        if decision_ok
        else f"missing options or recommendation (options={has_options}, recommendation={has_recommendation})",
    ))

    # If GRILLING.md exists under ASTACK_HOME, verify it lives under architecture/ and tracks open branches + cost ledger
    if grilling_files:
        grilling_ok = arch_grilling.is_file() and ("cost" in grilling_text.lower() or "ledger" in grilling_text.lower())
        checks.append((
            "grilling-snapshot-valid",
            grilling_ok,
            f"valid snapshot at {arch_grilling.name}"
            if grilling_ok
            else f"GRILLING.md missing expected path ({arch_grilling}) or cost ledger",
        ))

    sec = _eval_kit.check_no_secrets([combined])
    checks.append(("no-secrets", not sec, "; ".join(sec) if sec else "no secrets"))

    leaks = _eval_kit.check_no_internal_leaks([final_text])
    checks.append(("no-internal-leaks", not leaks, "; ".join(leaks) if leaks else "no internal leaks"))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
