#!/usr/bin/env python3
"""Executable verifier for `capstone-cross-repo-unland`."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

_FLOATING_REFS = {"main", "master", "latest", "head", "develop", "dev", "origin/main", "origin/master"}
_REF_KEYS = {"ref", "sha", "commit", "commit_sha", "pinned_sha", "merge_sha", "head_sha", "tag", "version", "artifact_ref"}


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


def _git_out(repo: Path, *args: str) -> str:
    proc = _git(repo, *args)
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def _cited_lines(text: str, filename: str) -> list[int]:
    return [int(m.group(1)) for m in re.finditer(rf"{re.escape(filename)}:(\d+)", text)]


def _find_floating_refs(obj: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = str(k).lower()
            child = f"{path}.{k}"
            if isinstance(v, str) and (kl in _REF_KEYS or any(t in kl for t in ("ref", "sha", "commit"))):
                if v.strip().lower() in _FLOATING_REFS:
                    hits.append(f"{child}={v!r}")
            else:
                hits.extend(_find_floating_refs(v, child))
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            hits.extend(_find_floating_refs(item, f"{path}[{idx}]"))
    return hits


def _match_step(steps: list[dict[str, Any]], repo_name: str) -> tuple[int, dict[str, Any]] | None:
    for idx, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        repo_val = str(step.get("repo", "")).strip().rstrip("/")
        step_id = str(step.get("id", "")).lower()
        if repo_val == repo_name or repo_val.endswith(f"/{repo_name}") or repo_name.split("-")[-1] in step_id:
            if repo_name == "repo-core" and "service" in repo_val:
                continue
            if repo_name == "repo-service" and "core" in repo_val:
                continue
            return idx, step
    return None


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo_core = ws / "repo-core"
    repo_service = ws / "repo-service"
    blast_path = ws / "program" / "BLAST_RADIUS.md"
    plan_path = ws / "program" / "release-plan.json"
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo_core.is_dir() or not repo_service.is_dir():
        checks.append(("workspace-intact", False, "missing repo-core or repo-service"))
        return _eval_kit.report_and_exit(checks)

    commit_a = (ws / "program" / "commit_a.txt").read_text(encoding="utf-8").strip()
    commit_b = (ws / "program" / "commit_b.txt").read_text(encoding="utf-8").strip()
    commit_c = (ws / "program" / "commit_c.txt").read_text(encoding="utf-8").strip()
    svc_base = (ws / "program" / "service_base_sha.txt").read_text(encoding="utf-8").strip()

    # 1. Both repos clean
    c_clean, c_msg = _eval_kit.check_git_clean(repo_core)
    s_clean, s_msg = _eval_kit.check_git_clean(repo_service)
    checks.append((
        "repos-clean",
        c_clean and s_clean,
        "repo-core and repo-service clean" if (c_clean and s_clean) else f"core: {c_msg}; service: {s_msg}",
    ))

    # 2. program/BLAST_RADIUS.md cites all 3 repo-service callers + int/dict TypeError failure mode
    blast_text = blast_path.read_text(encoding="utf-8", errors="replace") if blast_path.is_file() else ""
    b_low = blast_text.lower()
    bill_lines = _cited_lines(blast_text, "billing.py")
    inv_lines = _cited_lines(blast_text, "invoices.py")
    wh_lines = _cited_lines(blast_text, "webhooks.py")
    callers_ok = (
        any(10 <= ln <= 25 for ln in bill_lines)
        and any(10 <= ln <= 22 for ln in inv_lines)
        and any(4 <= ln <= 18 for ln in wh_lines)
    )
    failure_ok = ("dict" in b_low and "int" in b_low) or ("typeerror" in b_low)
    checks.append((
        "blast-radius-report-valid",
        len(blast_text.strip()) >= 150 and callers_ok and failure_ok,
        f"billing.py:{bill_lines}, invoices.py:{inv_lines}, webhooks.py:{wh_lines}, failure_mode={failure_ok}"
        if (len(blast_text.strip()) >= 150 and callers_ok and failure_ok)
        else f"chars={len(blast_text.strip())}, billing={bill_lines}, invoices={inv_lines}, webhooks={wh_lines}, failure={failure_ok}",
    ))

    # 3. Commit B safely reverted in repo-core (Commit C preserved in ancestry, zero history rewrite)
    anc_c = _git(repo_core, "merge-base", "--is-ancestor", commit_c, "HEAD").returncode == 0
    core_head = _git_out(repo_core, "rev-parse", "HEAD").strip()
    svc_head = _git_out(repo_service, "rev-parse", "HEAD").strip()
    commits_after_c = int(_git_out(repo_core, "rev-list", "--count", f"{commit_c}..HEAD").strip()) if anc_c else 0
    hist_ok = anc_c and core_head != commit_c and (1 <= commits_after_c <= 2)
    checks.append((
        "history-and-commit-c-preserved",
        hist_ok,
        f"commit C ({commit_c[:8]}) preserved in ancestry with {commits_after_c} revert commit(s)"
        if hist_ok
        else f"anc_c={anc_c}, head={core_head[:8]}, commit_c={commit_c[:8]}, after_c={commits_after_c}",
    ))

    log_after_c = _git_out(repo_core, "log", "--format=%B", f"{commit_c}..HEAD") if anc_c else ""
    revert_msg_ok = ("revert" in log_after_c.lower()) or (commit_b[:7] in log_after_c)
    checks.append((
        "revert-commit-recorded",
        revert_msg_ok,
        "revert commit references revert / commit B"
        if revert_msg_ok
        else f"revert message missing revert or {commit_b[:7]}: {log_after_c[:120]!r}",
    ))

    orig_pricing = _git_out(repo_core, "show", f"{commit_a}:src/pricing.py")
    curr_pricing = (repo_core / "src" / "pricing.py").read_text(encoding="utf-8")
    checks.append((
        "commit-b-reverted",
        curr_pricing == orig_pricing,
        "repo-core/src/pricing.py restored to Commit A integer-cents contract"
        if curr_pricing == orig_pricing
        else "repo-core/src/pricing.py does not match Commit A",
    ))

    orig_chlog = _git_out(repo_core, "show", f"{commit_c}:docs/CHANGELOG.md")
    orig_readme = _git_out(repo_core, "show", f"{commit_c}:README.md")
    curr_chlog = (repo_core / "docs" / "CHANGELOG.md").read_text(encoding="utf-8") if (repo_core / "docs" / "CHANGELOG.md").is_file() else ""
    curr_readme = (repo_core / "README.md").read_text(encoding="utf-8") if (repo_core / "README.md").is_file() else ""
    docs_ok = (curr_chlog == orig_chlog) and (curr_readme == orig_readme)
    checks.append((
        "commit-c-docs-preserved",
        docs_ok,
        "Commit C docs/CHANGELOG.md and README.md preserved intact"
        if docs_ok
        else "Commit C docs were lost or altered",
    ))

    # 4. program/release-plan.json pinned with exact post-revert SHAs in order repo-core -> repo-service
    plan_raw = plan_path.read_text(encoding="utf-8", errors="replace") if plan_path.is_file() else ""
    try:
        plan = json.loads(plan_raw)
    except json.JSONDecodeError as exc:
        plan = None
        checks.append(("release-plan-valid", False, f"invalid JSON: {exc}"))
    else:
        if not isinstance(plan, dict) or not isinstance(plan.get("steps"), list) or len(plan["steps"]) < 2:
            checks.append(("release-plan-valid", False, "release-plan.json missing steps list with >=2 steps"))
        else:
            steps = plan["steps"]
            floating = _find_floating_refs(plan)
            core_match = _match_step(steps, "repo-core")
            svc_match = _match_step(steps, "repo-service")
            if floating or core_match is None or svc_match is None:
                checks.append((
                    "release-plan-valid",
                    False,
                    f"floating={floating}, core_found={core_match is not None}, svc_found={svc_match is not None}",
                ))
            else:
                c_idx, c_step = core_match
                s_idx, s_step = svc_match
                c_id = str(c_step.get("id", ""))
                s_id = str(s_step.get("id", ""))
                c_pinned = core_head in json.dumps(c_step)
                s_pinned = svc_head in json.dumps(s_step)
                c_deps = c_step.get("depends_on") or []
                s_deps = s_step.get("depends_on") or []
                order_ok = (
                    c_idx < s_idx
                    and isinstance(s_deps, list)
                    and c_id in s_deps
                    and isinstance(c_deps, list)
                    and s_id not in c_deps
                )
                all_plan_ok = c_pinned and s_pinned and order_ok
                checks.append((
                    "release-plan-valid",
                    all_plan_ok,
                    f"pinned repo-core={core_head[:12]} -> repo-service={svc_head[:12]} (zero floating refs)"
                    if all_plan_ok
                    else f"core_pinned={c_pinned}, svc_pinned={s_pinned}, order_ok={order_ok} (c@{c_idx} deps={c_deps}, s@{s_idx} deps={s_deps})",
                ))

    # 5. BOTH test suites pass
    ut_core_ok, ut_core_msg = _eval_kit.run_unittest(repo_core)
    checks.append(("repo-core-unittest", ut_core_ok, ut_core_msg))

    ut_svc_ok, ut_svc_msg = _eval_kit.run_unittest(repo_service)
    checks.append(("repo-service-unittest", ut_svc_ok, ut_svc_msg))

    # 6. Gates intact on both repos + zero secrets/leaks
    g_core_ok, g_core_msg = _eval_kit.check_gates_intact(repo_core, base_ref=commit_a)
    g_svc_ok, g_svc_msg = _eval_kit.check_gates_intact(repo_service, base_ref=svc_base)
    checks.append((
        "gates-intact",
        g_core_ok and g_svc_ok,
        "gates intact in both repos" if (g_core_ok and g_svc_ok) else f"core: {g_core_msg}; service: {g_svc_msg}",
    ))

    texts = [final_text, blast_text, plan_raw]
    sec_hits = _eval_kit.check_no_secrets(texts)
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks(texts)
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
