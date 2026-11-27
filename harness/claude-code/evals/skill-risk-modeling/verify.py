#!/usr/bin/env python3
"""Objective post-run verifier for skill-risk-modeling."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("repo-exists", False, f"missing repo directory: {repo}"))
        return _eval_kit.report_and_exit(checks)

    ok_clean, msg_clean = _eval_kit.check_git_clean(repo)
    checks.append(("repo-clean", ok_clean, msg_clean))

    out_path = ws / "program" / "RISK_SCORE.json"
    if not out_path.is_file():
        checks.append(("risk-score-file", False, "missing program/RISK_SCORE.json"))
        return _eval_kit.report_and_exit(checks)

    try:
        data = json.loads(out_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        checks.append(("valid-json", False, f"invalid JSON in program/RISK_SCORE.json: {exc}"))
        return _eval_kit.report_and_exit(checks)

    ch_risk = data.get("change_risk")
    ok_ch = isinstance(ch_risk, (int, float)) and not isinstance(ch_risk, bool) and 0.0 <= float(ch_risk) < 1.0
    checks.append(("change-risk-normalized", ok_ch, f"change_risk={ch_risk!r}"))

    vecs = data.get("vectors") if isinstance(data.get("vectors"), list) else []
    by_name = {str(v.get("name")): v for v in vecs if isinstance(v, dict)}
    ok_vecs = "core" in by_name and "docs" in by_name and all(
        isinstance(by_name[n].get("risk"), (int, float))
        and not isinstance(by_name[n].get("risk"), bool)
        and 0.0 <= float(by_name[n]["risk"]) < 1.0
        and isinstance(by_name[n].get("share"), (int, float))
        for n in ("core", "docs")
        if n in by_name
    )
    checks.append(("vectors-scored", ok_vecs, f"vectors={sorted(by_name)}"))

    fc = data.get("finder_checks") if isinstance(data.get("finder_checks"), dict) else {}
    ok_fc = (
        fc.get("level_status") == "unverified"
        and "level_trusted" not in fc
        and "fix_rate_stable" not in fc
        and fc.get("reverts_checked", 0) >= 1
    )
    checks.append(("finder-checks-honest", ok_fc, f"finder_checks={fc!r}"))
    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
