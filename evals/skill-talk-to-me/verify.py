#!/usr/bin/env python3
"""Executable verifier for `skill-talk-to-me`."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

_MERKLE_FUNCS = ("hash_leaf", "hash_node", "build_levels", "inclusion_proof", "verify_proof")


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    final_text = _eval_kit.final_text_from_env()
    guide_path = ws / "program" / "GUIDE.md"
    guide_text = guide_path.read_text(encoding="utf-8", errors="replace") if guide_path.is_file() else ""
    combined = "\n".join(part for part in (final_text, guide_text) if part.strip())
    low = combined.lower()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("repo-exists", False, f"missing repo directory: {repo}"))
        return _eval_kit.report_and_exit(checks)

    clean_ok, clean_detail = _eval_kit.check_git_clean(repo)
    checks.append(("repo-git-clean", clean_ok, clean_detail))

    has_substance = len(combined.strip()) >= 300
    checks.append((
        "explanation-present",
        has_substance,
        f"explanation length {len(combined.strip())} chars" if has_substance else f"explanation missing or too short ({len(combined.strip())} chars)",
    ))

    matched_funcs = [fn for fn in _MERKLE_FUNCS if fn in combined]
    refs_merkle = "merkle.py" in low and len(matched_funcs) >= 3
    checks.append((
        "grounded-in-merkle-py",
        refs_merkle,
        f"references src/merkle.py and functions {matched_funcs}"
        if refs_merkle
        else f"merkle.py_in_text={'merkle.py' in low}, funcs={matched_funcs}",
    ))

    has_mermaid = bool(
        re.search(r"```mermaid\s+.*?(?:flowchart|graph|sequenceDiagram|stateDiagram)", combined, re.S)
    )
    checks.append((
        "mermaid-diagram",
        has_mermaid,
        "Mermaid diagram present" if has_mermaid else "missing Mermaid diagram",
    ))

    has_worked_example = (
        ("sibling" in low or "proof" in low)
        and "root" in low
        and bool(re.search(r"(tx-a|tx-b|step\s*1|input|example)", low))
        and ("left" in low or "right" in low)
    )
    checks.append((
        "concrete-worked-example",
        has_worked_example,
        "walked step-by-step sibling/root example present"
        if has_worked_example
        else "missing concrete worked example tracing sibling hashes to root",
    ))

    has_analogy_and_pitfall = (
        bool(re.search(r"\b(analogy|like\s+a|breaks\s+down|limit|pitfall|second-preimage|0x00|0x01|duplicat)", low))
        and bool(re.search(r"\b(breaks\s+down|pitfall|second-preimage|odd|duplicat|attack|caveat|limit)", low))
    )
    checks.append((
        "analogy-and-pitfalls",
        has_analogy_and_pitfall,
        "includes analogy/limits and practical pitfalls"
        if has_analogy_and_pitfall
        else "missing analogy breakdown or practical pitfalls",
    ))

    sec_hits = _eval_kit.check_no_secrets([combined])
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks([combined])
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
