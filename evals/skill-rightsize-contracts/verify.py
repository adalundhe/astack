#!/usr/bin/env python3
"""Objective post-run verifier for skill-rightsize-contracts."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    astack_home = _eval_kit.astack_home_from_env(ws).resolve()
    astack_tools = Path(__file__).resolve().parents[2] / "bin" / "astack-tools"
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("repo-exists", False, f"missing repo directory: {repo}"))
        return _eval_kit.report_and_exit(checks)

    ok_clean, msg_clean = _eval_kit.check_git_clean(repo)
    checks.append(("repo-clean", ok_clean, msg_clean))

    env = {**os.environ, "ASTACK_HOME": str(astack_home)}
    proc = subprocess.run(
        [sys.executable, "-B", str(astack_tools), "docs", "list", "--project", "payments-sdk", "--subdir", "contracts", "--json"],
        capture_output=True,
        text=True,
        env=env,
    )
    docs_entries: list[dict[str, object]] = []
    if proc.returncode == 0:
        try:
            payload = json.loads(proc.stdout)
            raw = payload.get("docs", [])
            if isinstance(raw, list):
                docs_entries = [e for e in raw if isinstance(e, dict)]
        except json.JSONDecodeError:
            pass

    catalog_files: list[Path] = []
    for ent in docs_entries:
        p = Path(str(ent.get("path", ""))).resolve()
        if p.is_file() and p.stat().st_size > 0:
            catalog_files.append(p)
        elif p.is_dir():
            for child in sorted(p.rglob("*")):
                if child.is_file() and child.stat().st_size > 0:
                    catalog_files.append(child.resolve())

    checks.append((
        "catalog-published-via-astack-tools",
        proc.returncode == 0 and bool(catalog_files),
        f"astack-tools docs list found {len(catalog_files)} catalog file(s): {[f.name for f in catalog_files]}"
        if proc.returncode == 0 and catalog_files
        else f"no contract catalog found via astack-tools docs list (rc={proc.returncode})",
    ))

    catalog_texts = [p.read_text(encoding="utf-8", errors="replace") for p in catalog_files]
    combined = "\n\n".join(catalog_texts).strip()
    low = combined.lower()

    has_sdk_line = bool(re.search(r"sdk\.py:\d+", combined))
    checks.append((
        "cites-sdk-file-line",
        has_sdk_line,
        "catalog cites exact src/sdk.py:<line> locations"
        if has_sdk_line
        else "catalog missing src/sdk.py:<line> citations",
    ))

    bloated_tokens = {
        "amount_alias": ("amount" in low and "amount_cents" in low),
        "currency_alias": ("currency_code" in low and "currency" in low),
        "customer_alias": ("cust_id" in low and "customer_id" in low),
        "timeout_alias": ("timeout_seconds" in low and "timeout_ms" in low),
        "retry_redundant": ("retry_enabled" in low and "max_retries" in low),
        "environment_derivable": "environment" in low,
        "dead_legacy_xml": "legacy_xml_envelope" in low,
    }
    matched_bloat = [k for k, v in bloated_tokens.items() if v]
    flags_hidden_env = "payments_sdk_force_sync_fallback" in low
    checks.append((
        "identifies-aliases-bloat-and-hidden-toggle",
        len(matched_bloat) >= 5 and flags_hidden_env,
        f"matched {len(matched_bloat)}/7 bloat defects ({', '.join(matched_bloat)}), hidden_env_flagged={flags_hidden_env}",
    ))

    has_tiers = bool(re.search(r"\b(tier\s*[0-3]|level\s*[0-3]|rung\s*[0-3]|stepped[- ]complexity|progressive)\b", low))
    has_defaults = bool(re.search(r"\b(default|defaults|optional|transport|advanced|config)\b", low))
    has_migration = bool(re.search(r"\b(deprecat|migrat|compatib|rollout|breaking|v2|warn)\b", low))
    checks.append((
        "stepped-complexity-tiers-and-migration",
        has_tiers and has_defaults and has_migration,
        f"tiers={has_tiers}, defaults={has_defaults}, migration={has_migration}",
    ))

    sec_hits = _eval_kit.check_no_secrets([combined, final_text])
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks([combined, final_text])
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
