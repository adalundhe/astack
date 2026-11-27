#!/usr/bin/env python3
"""Objective post-run verifier for skill-cross-repo."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

FLOATING_REFS = {"main", "master", "latest", "head", "develop", "dev", "origin/main", "origin/master"}
REF_KEYS = {"ref", "sha", "commit", "commit_sha", "pinned_sha", "merge_sha", "head_sha", "tag", "version", "artifact_ref"}


def _git_head(repo: Path) -> str:
    proc = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
    return proc.stdout.strip()


def _find_floating_refs(obj: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = str(k).lower()
            child_path = f"{path}.{k}"
            if isinstance(v, str) and (kl in REF_KEYS or any(tok in kl for tok in ("ref", "sha", "commit"))):
                if v.strip().lower() in FLOATING_REFS:
                    hits.append(f"{child_path}={v!r}")
            else:
                hits.extend(_find_floating_refs(v, child_path))
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            hits.extend(_find_floating_refs(item, f"{path}[{idx}]"))
    return hits


def _step_contains_sha(step: dict[str, Any], expected_sha: str) -> bool:
    raw = json.dumps(step)
    return expected_sha in raw


def _match_step(steps: list[dict[str, Any]], repo_name: str) -> tuple[int, dict[str, Any]] | None:
    for idx, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        repo_val = str(step.get("repo", "")).strip().rstrip("/")
        step_id = str(step.get("id", "")).lower()
        if repo_val == repo_name or repo_val.endswith(f"/{repo_name}") or repo_name.split("-")[-1] in step_id:
            if repo_name == "repo-lib" and "app" in repo_val:
                continue
            if repo_name == "repo-app" and "lib" in repo_val:
                continue
            return idx, step
    return None


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo_lib = ws / "repo-lib"
    repo_app = ws / "repo-app"
    plan_path = ws / "program" / "release-plan.json"
    final_text = _eval_kit.final_text_from_env()

    checks: list[tuple[str, bool, str]] = []

    ok_lib_clean, msg_lib_clean = _eval_kit.check_git_clean(repo_lib)
    ok_app_clean, msg_app_clean = _eval_kit.check_git_clean(repo_app)
    checks.append((
        "repos-clean",
        ok_lib_clean and ok_app_clean,
        "repo-lib and repo-app working trees clean"
        if (ok_lib_clean and ok_app_clean)
        else f"repo-lib: {msg_lib_clean}; repo-app: {msg_app_clean}",
    ))

    lib_sha = _git_head(repo_lib)
    app_sha = _git_head(repo_app)

    plan_raw = plan_path.read_text(encoding="utf-8") if plan_path.is_file() else ""
    try:
        plan = json.loads(plan_raw)
    except json.JSONDecodeError as exc:
        plan = None
        checks.append(("valid-json", False, f"invalid JSON in program/release-plan.json: {exc}"))
    else:
        ok_obj = isinstance(plan, dict) and isinstance(plan.get("steps"), list) and len(plan["steps"]) >= 2
        checks.append(("valid-json", ok_obj, f"valid JSON with {len(plan.get('steps', []))} steps" if ok_obj else "missing steps list"))

    if isinstance(plan, dict) and isinstance(plan.get("steps"), list):
        steps = plan["steps"]
        floating = _find_floating_refs(plan)
        checks.append((
            "no-floating-refs",
            not floating,
            "zero floating refs" if not floating else f"floating ref(s) found: {', '.join(floating)}",
        ))

        lib_match = _match_step(steps, "repo-lib")
        app_match = _match_step(steps, "repo-app")
        if lib_match is None or app_match is None:
            checks.append(("steps-identified", False, f"could not identify repo-lib ({lib_match is not None}) and repo-app ({app_match is not None}) steps"))
        else:
            lib_idx, lib_step = lib_match
            app_idx, app_step = app_match
            lib_id = str(lib_step.get("id", ""))
            app_id = str(app_step.get("id", ""))

            lib_pinned = _step_contains_sha(lib_step, lib_sha)
            app_pinned = _step_contains_sha(app_step, app_sha)
            checks.append((
                "exact-pinned-shas",
                lib_pinned and app_pinned,
                f"pinned repo-lib={lib_sha[:12]} and repo-app={app_sha[:12]}"
                if (lib_pinned and app_pinned)
                else f"missing exact 40-char SHA(s): lib_pinned={lib_pinned} ({lib_sha}), app_pinned={app_pinned} ({app_sha})",
            ))

            lib_deps = lib_step.get("depends_on") or []
            app_deps = app_step.get("depends_on") or []
            order_ok = (
                lib_idx < app_idx
                and isinstance(app_deps, list)
                and lib_id in app_deps
                and isinstance(lib_deps, list)
                and app_id not in lib_deps
            )
            checks.append((
                "topological-order",
                order_ok,
                f"repo-lib ({lib_id}@{lib_idx}) precedes repo-app ({app_id}@{app_idx}) with depends_on={app_deps}"
                if order_ok
                else f"wrong order or deps: lib@{lib_idx} deps={lib_deps}, app@{app_idx} deps={app_deps}",
            ))

    sec = _eval_kit.check_no_secrets([plan_raw, final_text])
    checks.append(("no-secrets", not sec, "; ".join(sec) if sec else "no secrets"))

    leaks = _eval_kit.check_no_internal_leaks([final_text])
    checks.append(("no-internal-leaks", not leaks, "; ".join(leaks) if leaks else "no internal leaks"))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
