#!/usr/bin/env python3
"""Executable verifier for `skill-next-step`."""
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
    cat_proc = subprocess.run(
        [sys.executable, "-B", str(_ASTACK_TOOLS), "docs", "list", "--project", "cli-kit", "--subdir", "contracts", "--json"],
        cwd=ws,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    cat_ok = False
    if cat_proc.returncode == 0:
        try:
            payload = json.loads(cat_proc.stdout)
            docs = payload.get("docs") or []
            cat_ok = any("cli-contract.md" in str(d.get("name", "")) for d in docs)
        except json.JSONDecodeError:
            cat_ok = False
    checks.append(("contract-catalog-intact", cat_ok, "cli-contract.md present via astack-tools docs list" if cat_ok else "missing cli-contract.md"))

    next_steps_path = ws / "program" / "NEXT_STEPS.md"
    next_steps_text = next_steps_path.read_text(encoding="utf-8", errors="replace") if next_steps_path.is_file() else ""
    combined = "\n".join(part for part in (next_steps_text, final_text) if part.strip())
    low = combined.lower()

    has_body = len(combined.strip()) >= 200
    checks.append((
        "recommendations-present",
        has_body,
        f"recommendations text ({len(combined.strip())} chars)" if has_body else "missing or too short recommendations",
    ))

    refs_contract = (
        ("cli-contract.md" in low or ("--config" in low and "cli_kit_config" in low))
        and ("src/cli.py" in low or "cli.py" in low)
        and "list" in low
        and "run" in low
    )
    checks.append((
        "references-existing-contract-and-code",
        refs_contract,
        "references cli-contract.md / existing CLI flags and src/cli.py"
        if refs_contract
        else "missing reference to existing contract or src/cli.py",
    ))

    has_stepped_tiers = bool(re.search(r"\b(tier\s*[012]|rung|stepped|progression|zero regression|unchanged)\b", low)) and bool(
        re.search(r"(--json|--dry-run|--tag)", low)
    )
    checks.append((
        "tiered-minimal-contract-delta",
        has_stepped_tiers,
        "maps stepped tiers/rungs with concrete minimal flag delta(s)"
        if has_stepped_tiers
        else "missing tiered/rung framing or concrete minimal CLI delta (--json / --dry-run / --tag)",
    ))

    has_user_impact = bool(re.search(r"\b(awk|cut|preview|pre-flight|chain\w*|friction|manual|ci)\b", low)) and bool(
        re.search(r"(?:^|\n)\s*(?:1\.|##\s*1|###\s*1|\*\*1\.)", combined)
        and re.search(r"(?:^|\n)\s*(?:2\.|##\s*2|###\s*2|\*\*2\.)", combined)
    )
    checks.append((
        "ranked-user-impact-recommendations",
        has_user_impact,
        "at least 2 ranked proposals tied to concrete user friction"
        if has_user_impact
        else "missing ranked (>=2) proposals or concrete user friction mapping",
    ))

    sec_hits = _eval_kit.check_no_secrets([combined])
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks([combined])
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
