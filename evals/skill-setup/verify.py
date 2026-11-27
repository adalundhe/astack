#!/usr/bin/env python3
"""Objective post-run verifier for skill-setup."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

REQUIRED_TIMERS = (
    "worker_minutes",
    "reviewer_minutes",
    "researcher_minutes",
    "check_in_minutes",
    "wind_down_minutes",
)


def _is_pos_int(val: Any) -> bool:
    return isinstance(val, int) and not isinstance(val, bool) and val > 0


def _valid_model_entry(entry: Any) -> bool:
    return (
        isinstance(entry, dict)
        and isinstance(entry.get("provider"), str)
        and bool(entry["provider"].strip())
        and isinstance(entry.get("model"), str)
        and bool(entry["model"].strip())
    )


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    settings_path = ws / "program" / "settings.json"
    final_text = _eval_kit.final_text_from_env()

    checks: list[tuple[str, bool, str]] = []

    ok_clean, msg_clean = _eval_kit.check_git_clean(repo)
    checks.append(("repo-clean", ok_clean, msg_clean))

    raw = settings_path.read_text(encoding="utf-8") if settings_path.is_file() else ""
    try:
        cfg = json.loads(raw)
    except json.JSONDecodeError as exc:
        cfg = None
        checks.append(("valid-json", False, f"invalid JSON in program/settings.json: {exc}"))
    else:
        ok_dict = isinstance(cfg, dict)
        checks.append(("valid-json", ok_dict, "program/settings.json is valid JSON object" if ok_dict else "expected JSON object"))

    if isinstance(cfg, dict):
        # 1. Timers
        bad_timers = [k for k in REQUIRED_TIMERS if not _is_pos_int(cfg.get(k))]
        wind_ok = False
        if not bad_timers:
            wind_ok = cfg["wind_down_minutes"] < min(
                cfg["worker_minutes"], cfg["reviewer_minutes"], cfg["researcher_minutes"]
            )
        timers_ok = not bad_timers and wind_ok
        checks.append((
            "timers-valid",
            timers_ok,
            f"all 5 timers valid ({', '.join(f'{k}={cfg[k]}' for k in REQUIRED_TIMERS)})"
            if timers_ok
            else f"invalid/missing timers: {bad_timers or 'wind_down_minutes must be < min(role timers)'}",
        ))

        # 2. Roles (and retired roles.reviewer removed)
        roles = cfg.get("roles")
        role_errs: list[str] = []
        if not isinstance(roles, dict):
            role_errs.append("roles must be an object")
        else:
            for rname in ("lead", "worker", "researcher"):
                if not _valid_model_entry(roles.get(rname)):
                    role_errs.append(f"roles.{rname} invalid or missing")
            if "reviewer" in roles:
                role_errs.append("retired roles.reviewer was not removed")
        checks.append((
            "roles-valid",
            not role_errs,
            "roles has valid lead/worker/researcher and no retired roles.reviewer"
            if not role_errs
            else "; ".join(role_errs),
        ))

        # 3. Reviewer pool
        pool = cfg.get("reviewer_pool")
        pool_errs: list[str] = []
        if not isinstance(pool, list) or len(pool) < 2:
            pool_errs.append("reviewer_pool must be a list with >=2 entries")
        else:
            for idx, item in enumerate(pool):
                if not _valid_model_entry(item):
                    pool_errs.append(f"reviewer_pool[{idx}] missing valid provider/model")
            providers = {str(item.get("provider", "")).lower() for item in pool if isinstance(item, dict)}
            if "openai" not in providers:
                pool_errs.append("migrated openai reviewer entry missing from reviewer_pool")
        checks.append((
            "reviewer-pool-valid",
            not pool_errs,
            f"reviewer_pool valid with {len(pool)} entries" if not pool_errs and isinstance(pool, list) else "; ".join(pool_errs),
        ))

        # 4. Autonomy
        aut = cfg.get("autonomy")
        aut_errs: list[str] = []
        if not isinstance(aut, dict):
            aut_errs.append("autonomy missing or not an object")
        else:
            mode = aut.get("mode")
            allow = aut.get("allow")
            deny = aut.get("deny")
            if mode not in ("supervised", "unattended"):
                aut_errs.append(f"invalid autonomy.mode: {mode!r}")
            if not isinstance(allow, list) or not all(isinstance(x, str) for x in allow):
                aut_errs.append("autonomy.allow must be a list of strings")
            if not isinstance(deny, list) or not all(isinstance(x, str) for x in deny) or not deny:
                aut_errs.append("autonomy.deny must be a non-empty list of strings")
            if isinstance(allow, list) and isinstance(deny, list) and (set(allow) & set(deny)):
                aut_errs.append(f"autonomy allow/deny overlap: {sorted(set(allow) & set(deny))}")
        checks.append((
            "autonomy-valid",
            not aut_errs,
            f"autonomy valid (mode={aut.get('mode')!r})" if not aut_errs and isinstance(aut, dict) else "; ".join(aut_errs),
        ))

        # 5. Automation
        auto = cfg.get("automation")
        auto_ok = isinstance(auto, dict) and auto.get("mode") in ("agentic-only", "python-stack")
        checks.append((
            "automation-valid",
            auto_ok,
            f"automation valid (mode={auto.get('mode')!r})" if auto_ok and isinstance(auto, dict) else f"invalid/missing automation: {auto!r}",
        ))

    sec = _eval_kit.check_no_secrets([raw, final_text])
    checks.append(("no-secrets", not sec, "; ".join(sec) if sec else "no secrets"))

    leaks = [
        hit for hit in _eval_kit.check_no_internal_leaks([final_text])
        if "'reviewer_pool'" not in hit
    ]
    checks.append(("no-internal-leaks", not leaks, "; ".join(leaks) if leaks else "no internal leaks"))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
