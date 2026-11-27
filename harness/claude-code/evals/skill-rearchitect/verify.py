#!/usr/bin/env python3
"""Objective post-run verifier for skill-rearchitect."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    report_path = ws / "program" / "REARCHITECT.md"
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("repo-exists", False, f"missing repo directory: {repo}"))
        return _eval_kit.report_and_exit(checks)

    ok_clean, msg_clean = _eval_kit.check_git_clean(repo)
    checks.append(("repo-clean", ok_clean, msg_clean))

    report_text = report_path.read_text(encoding="utf-8", errors="replace").strip() if report_path.is_file() else ""
    combined = "\n\n".join(p for p in (report_text, final_text.strip()) if p)
    low = combined.lower()

    checks.append((
        "rearchitect-md-written",
        report_path.is_file() and len(report_text) >= 250,
        f"program/REARCHITECT.md exists ({len(report_text)} chars)"
        if report_path.is_file() and len(report_text) >= 250
        else f"missing or too short program/REARCHITECT.md ({len(report_text)} chars)",
    ))

    identifies_hotspots = (
        "sync.py" in low
        and "state.py" in low
        and bool(re.search(r"\b(churn|commits?|co-?change|hotspot|history|git\s+log)\b", low))
    )
    checks.append((
        "churn-hotspots-identified",
        identifies_hotspots,
        "identified high-churn co-change hotspots src/sync.py and src/state.py from git history"
        if identifies_hotspots
        else "missing git churn hotspot identification for src/sync.py and src/state.py",
    ))

    identifies_circular = bool(re.search(r"(circular\s+import|bidirectional|cyclic|cycle|inline\s+import|deferred\s+import)", low))
    identifies_shared = "_shared_state" in low or ("shared" in low and ("global" in low or "mutable" in low or "dict" in low))
    checks.append((
        "structural-friction-diagnosed",
        identifies_circular and identifies_shared,
        f"circular_imports={identifies_circular}, shared_mutable_state={identifies_shared}",
    ))

    mermaid_blocks = re.findall(r"```mermaid\s*\n(.*?)```", combined, re.S | re.I)
    has_mermaid_diagram = any(
        re.search(r"\b(flowchart|graph|statediagram-v2|sequencediagram)\b", blk, re.I)
        and ("-->" in blk or "->" in blk)
        for blk in mermaid_blocks
    )
    checks.append((
        "mermaid-boundary-diagram",
        has_mermaid_diagram,
        f"found {len(mermaid_blocks)} valid Mermaid diagram block(s)"
        if has_mermaid_diagram
        else "missing fenced ```mermaid architecture diagram with directed edges",
    ))

    has_target_boundaries = bool(
        re.search(r"\b(unidirectional|acyclic|decoupl|one[- ]way|encapsulat|own(?:s|ership)|single\s+owner|store)\b", low)
    )
    has_migration_plan = bool(
        re.search(r"\b(migrat|phase|step\s*1|batch|incremental|pin(?:ning)?\s+test|dag|rollout)\b", low)
    )
    has_ranking = bool(re.search(r"\b(strong|worth\s+exploring|speculative|rank|top\s+pick|priority)\b", low))
    checks.append((
        "boundaries-ranking-and-migration",
        has_target_boundaries and has_migration_plan and has_ranking,
        f"target_boundaries={has_target_boundaries}, migration_plan={has_migration_plan}, strength_ranking={has_ranking}",
    ))

    sec_hits = _eval_kit.check_no_secrets([combined])
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks([combined])
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
