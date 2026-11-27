#!/usr/bin/env python3
"""Objective post-run verifier for skill-slates."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

REQUIRED_BRANCHES = ("lane/auth", "lane/billing")


def _git_out(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
    return proc.stdout


def _parse_worktrees(repo: Path) -> dict[str, Path]:
    """Return mapping branch_name -> resolved Path for all branch-attached worktrees."""
    out = _git_out(repo, "worktree", "list", "--porcelain")
    branch_to_path: dict[str, Path] = {}
    cur_path: Path | None = None
    cur_branch: str | None = None
    for raw_line in out.splitlines() + [""]:
        line = raw_line.strip()
        if not line:
            if cur_path is not None and cur_branch is not None:
                branch_to_path[cur_branch] = cur_path.resolve()
            cur_path = None
            cur_branch = None
            continue
        if line.startswith("worktree "):
            cur_path = Path(line.split(" ", 1)[1].strip())
        elif line.startswith("branch refs/heads/"):
            cur_branch = line.removeprefix("branch refs/heads/").strip()
    return branch_to_path


def _is_inside(candidate: Path, parent: Path) -> bool:
    try:
        candidate.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _resolve_reported_path(ws: Path, raw_path: str) -> Path:
    p = Path(raw_path)
    if not p.is_absolute():
        p = ws / p
    return p.resolve()


def _extract_workspace_map(data: Any, ws: Path) -> dict[str, Path]:
    """Extract branch -> resolved path from flexible workspaces.json shapes."""
    found: dict[str, Path] = {}

    def _visit_entry(entry: Any, key_hint: str = "") -> None:
        if isinstance(entry, str):
            if key_hint in REQUIRED_BRANCHES:
                found[key_hint] = _resolve_reported_path(ws, entry)
            elif f"lane/{key_hint}" in REQUIRED_BRANCHES:
                found[f"lane/{key_hint}"] = _resolve_reported_path(ws, entry)
            return
        if not isinstance(entry, dict):
            return
        branch = str(entry.get("branch") or entry.get("lane") or entry.get("name") or key_hint).strip()
        if branch in ("auth", "billing"):
            branch = f"lane/{branch}"
        path_val = entry.get("path") or entry.get("worktree") or entry.get("dir") or entry.get("workspace")
        if branch in REQUIRED_BRANCHES and isinstance(path_val, str) and path_val.strip():
            found[branch] = _resolve_reported_path(ws, path_val.strip())

    if isinstance(data, list):
        for item in data:
            _visit_entry(item)
    elif isinstance(data, dict):
        for container_key in ("workspaces", "worktrees", "lanes"):
            sub = data.get(container_key)
            if isinstance(sub, list):
                for item in sub:
                    _visit_entry(item)
            elif isinstance(sub, dict):
                for k, v in sub.items():
                    _visit_entry(v, key_hint=str(k))
        for k, v in data.items():
            if k not in ("workspaces", "worktrees", "lanes"):
                _visit_entry(v, key_hint=str(k))
    return found


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = (ws / "repo").resolve()
    manifest_path = ws / "program" / "workspaces.json"
    final_text = _eval_kit.final_text_from_env()

    checks: list[tuple[str, bool, str]] = []

    ok_clean, msg_clean = _eval_kit.check_git_clean(repo)
    main_branch = _git_out(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
    checks.append((
        "base-repo-clean-on-main",
        ok_clean and main_branch == "main",
        f"repo clean on {main_branch}" if (ok_clean and main_branch == "main") else f"clean={ok_clean} ({msg_clean}), branch={main_branch}",
    ))

    raw_manifest = manifest_path.read_text(encoding="utf-8") if manifest_path.is_file() else ""
    try:
        manifest = json.loads(raw_manifest)
    except json.JSONDecodeError as exc:
        manifest = None
        checks.append(("workspaces-json-valid", False, f"missing or invalid program/workspaces.json: {exc}"))
    else:
        reported = _extract_workspace_map(manifest, ws)
        has_both = all(b in reported for b in REQUIRED_BRANCHES)
        checks.append((
            "workspaces-json-valid",
            has_both,
            f"recorded paths for {', '.join(REQUIRED_BRANCHES)}"
            if has_both
            else f"missing lane entries in workspaces.json; parsed={sorted(reported)}",
        ))

    worktrees = _parse_worktrees(repo)
    wt_errors: list[str] = []
    wt_paths: list[Path] = []
    for branch in REQUIRED_BRANCHES:
        wt_path = worktrees.get(branch)
        if wt_path is None:
            wt_errors.append(f"no git worktree registered for {branch}")
            continue
        if not wt_path.is_dir():
            wt_errors.append(f"worktree directory missing: {wt_path}")
            continue
        if _is_inside(wt_path, repo):
            wt_errors.append(f"worktree for {branch} is inside ./repo ({wt_path})")
            continue
        wt_clean, wt_msg = _eval_kit.check_git_clean(wt_path)
        if not wt_clean:
            wt_errors.append(f"worktree for {branch} not clean: {wt_msg}")
            continue
        wt_paths.append(wt_path)

    if len(wt_paths) == len(REQUIRED_BRANCHES) and len(set(wt_paths)) != len(REQUIRED_BRANCHES):
        wt_errors.append("lane worktrees do not use distinct directories")

    checks.append((
        "worktrees-provisioned-and-isolated",
        not wt_errors and len(wt_paths) == len(REQUIRED_BRANCHES),
        f"2 isolated clean worktrees outside ./repo on {', '.join(REQUIRED_BRANCHES)}"
        if (not wt_errors and len(wt_paths) == len(REQUIRED_BRANCHES))
        else "; ".join(wt_errors),
    ))

    if manifest is not None:
        reported = _extract_workspace_map(manifest, ws)
        match_errors: list[str] = []
        for branch in REQUIRED_BRANCHES:
            rep_p = reported.get(branch)
            act_p = worktrees.get(branch)
            if rep_p is None or act_p is None or rep_p != act_p:
                match_errors.append(f"{branch}: reported={rep_p} vs registered={act_p}")
        checks.append((
            "manifest-matches-worktrees",
            not match_errors,
            "program/workspaces.json paths match registered git worktrees"
            if not match_errors
            else "; ".join(match_errors),
        ))

    sec = _eval_kit.check_no_secrets([raw_manifest, final_text])
    checks.append(("no-secrets", not sec, "; ".join(sec) if sec else "no secrets"))

    leaks = _eval_kit.check_no_internal_leaks([final_text])
    checks.append(("no-internal-leaks", not leaks, "; ".join(leaks) if leaks else "no internal leaks"))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
