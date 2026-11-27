#!/usr/bin/env python3
"""Shared stdlib-only verification and metadata kit for astack evals.

Used by `scripts/eval.py`, case `verify.py` scripts, `tests/test_build.py`,
and `tests/test_eval_verifiers.py`.
"""
from __future__ import annotations

import fnmatch
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

VALID_TIERS: tuple[str, ...] = ("smoke", "core", "deep")
TIER_ORDER: dict[str, int] = {"smoke": 0, "core": 1, "deep": 2}
VALID_KINDS: tuple[str, ...] = ("atomic", "capstone", "negative")

_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("sk-", re.compile(r"sk-[A-Za-z0-9_-]{8,}")),
    ("ghp_", re.compile(r"ghp_[A-Za-z0-9]{10,}")),
    ("gho_", re.compile(r"gho_[A-Za-z0-9]{10,}")),
    ("AKIA", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("PRIVATE KEY", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("Bearer", re.compile(r"Bearer [A-Za-z0-9._-]{16,}")),
)

# (token, case_sensitive)
_INTERNAL_LEAK_TOKENS: tuple[tuple[str, bool], ...] = (
    ("POOL EXHAUSTED", True),
    ("STOPPED (", True),
    ("coverage-map.md", False),
    ("astack-review-ledger", False),
    ("[rule:", False),
    ("reviewer_pool", False),
    ("settings.json default", False),
)

_FALLBACK_GATE_ADDED_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("@" + "unittest.skip", re.compile(r"@unittest\." + r"skip\b")),
    ("pytest.mark." + "skip", re.compile(r"pytest\.mark\." + r"skip\b")),
    ("xfail", re.compile(r"\bxfail\b")),
    ("#" + " noqa", re.compile(r"#\s*no" + r"qa\b", re.I)),
    ("type:" + " ignore", re.compile(r"type:\s*ig" + r"nore\b", re.I)),
)
_FALLBACK_DELETED_TEST_RE = re.compile(r"^\s*(?:async\s+)?def\s+test_\w+\s*\(")


def _unquote(val: str) -> str:
    val = val.strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
        return val[1:-1]
    return val


def _strip_yaml_comment(val: str) -> str:
    in_single = False
    in_double = False
    for idx, ch in enumerate(val):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            if idx == 0 or val[idx - 1].isspace():
                return val[:idx].rstrip()
    return val.strip()


def parse_case_yaml(path_or_text: Path | str) -> dict[str, Any]:
    """Parse a flat astack `case.yaml` file or string without external YAML libraries."""
    if isinstance(path_or_text, os.PathLike):
        text = Path(path_or_text).read_text(encoding="utf-8")
    elif isinstance(path_or_text, str):
        if "\n" not in path_or_text and path_or_text.endswith((".yaml", ".yml")) and Path(path_or_text).is_file():
            text = Path(path_or_text).read_text(encoding="utf-8")
        else:
            text = path_or_text
    else:
        raise TypeError(f"expected Path or str, got {type(path_or_text).__name__}")

    meta: dict[str, Any] = {
        "schema_version": "",
        "name": "",
        "tier": "",
        "kind": "",
        "skills": [],
        "scaffold_script": None,
    }
    section: str | None = None

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))

        if section == "skills" and stripped.startswith("-"):
            item_raw = _strip_yaml_comment(stripped[1:].strip())
            item = _unquote(item_raw)
            if item:
                meta["skills"].append(item)
            continue

        if indent > 0:
            if section == "context" and ":" in stripped:
                ckey, _, cval = stripped.partition(":")
                if ckey.strip() == "scaffold_script":
                    parsed = _unquote(_strip_yaml_comment(cval))
                    meta["scaffold_script"] = parsed or None
            continue

        section = None
        if ":" not in stripped:
            continue
        key, _, raw_val = stripped.partition(":")
        key = key.strip()
        val = _strip_yaml_comment(raw_val.strip())

        if key in ("schema_version", "name", "tier", "kind"):
            meta[key] = _unquote(val)
        elif key == "skills":
            if not val:
                section = "skills"
            elif val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                if inner:
                    for part in inner.split(","):
                        item = _unquote(part.strip())
                        if item:
                            meta["skills"].append(item)
            else:
                item = _unquote(val)
                if item:
                    meta["skills"].append(item)
        elif key == "context":
            if not val:
                section = "context"

    return meta


def check_no_secrets(texts: list[str], extra_tokens: tuple[str, ...] = ()) -> list[str]:
    """Sweep texts for leaked secret patterns and exact extra tokens."""
    findings: list[str] = []
    for idx, text in enumerate(texts):
        if not text:
            continue
        for label, rx in _SECRET_PATTERNS:
            if rx.search(text):
                findings.append(f"secret pattern '{label}' detected in text[{idx}]")
        for token in extra_tokens:
            if token and token in text:
                findings.append(f"forbidden secret token '{token}' detected in text[{idx}]")
    return findings


def check_no_internal_leaks(texts: list[str]) -> list[str]:
    """Sweep texts for leaked internal astack orchestration jargon."""
    findings: list[str] = []
    for idx, text in enumerate(texts):
        if not text:
            continue
        low = text.lower()
        for token, case_sensitive in _INTERNAL_LEAK_TOKENS:
            found = (token in text) if case_sensitive else (token.lower() in low)
            if found:
                findings.append(f"internal jargon {token!r} leaked in text[{idx}]")
    return findings


def check_git_clean(repo: Path) -> tuple[bool, str]:
    """Verify `git status --porcelain` is empty in `repo`."""
    proc = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return False, f"git status failed: {proc.stderr.strip() or proc.stdout.strip()}"
    dirty = proc.stdout.strip()
    if dirty:
        return False, f"working tree not clean:\n{dirty}"
    return True, "git working tree clean"


def _find_check_gates_script() -> Path | None:
    candidate = Path(__file__).resolve().parent.parent / "bin" / "astack-check-gates"
    return candidate if candidate.is_file() else None


def _fallback_check_gates_diff(repo: Path, base_ref: str) -> tuple[bool, str]:
    proc = subprocess.run(
        ["git", "-C", str(repo), "diff", "-M", "--unified=0", base_ref],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return False, f"git diff {base_ref} failed: {proc.stderr.strip()}"
    hits: list[str] = []
    for line in proc.stdout.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            content = line[1:]
            for label, rx in _FALLBACK_GATE_ADDED_PATTERNS:
                if rx.search(content):
                    hits.append(f"added {label}: {content.strip()[:100]}")
        elif line.startswith("-") and not line.startswith("---"):
            content = line[1:]
            if _FALLBACK_DELETED_TEST_RE.search(content):
                hits.append(f"deleted test: {content.strip()[:100]}")
    if hits:
        return False, "; ".join(hits)
    return True, "gates intact (fallback diff scan)"


def check_gates_intact(repo: Path, base_ref: str = "HEAD") -> tuple[bool, str]:
    """Run `bin/astack-check-gates` against `repo` (or fallback diff check) to verify no gates were gamed."""
    checker = _find_check_gates_script()
    if checker is None:
        return _fallback_check_gates_diff(repo, base_ref)

    invocations: list[list[str]] = []
    if base_ref == "HEAD":
        invocations.append([sys.executable, "-B", str(checker), "--repo", str(repo), "--working"])
    else:
        invocations.append([sys.executable, "-B", str(checker), f"{base_ref}..HEAD", "--repo", str(repo)])
        status = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain"],
            capture_output=True,
            text=True,
        )
        if status.returncode == 0 and status.stdout.strip():
            invocations.append([sys.executable, "-B", str(checker), "--repo", str(repo), "--working"])

    for cmd in invocations:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            detail = (proc.stdout.strip() or proc.stderr.strip() or f"exit {proc.returncode}")
            return False, detail

    return True, "gates intact"


def _unquote_git_path(raw: str) -> str:
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == '"' and raw[-1] == '"':
        return raw[1:-1]
    return raw


def check_scoped_writes(
    repo: Path,
    allowed_globs: list[str],
    base_ref: str = "HEAD",
) -> tuple[bool, str]:
    """Verify all modified/untracked files since `base_ref` match at least one glob in `allowed_globs`."""
    touched: set[str] = set()

    st = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain", "-uall"],
        capture_output=True,
        text=True,
    )
    if st.returncode != 0:
        return False, f"git status failed: {st.stderr.strip()}"
    for line in st.stdout.splitlines():
        if len(line) < 4:
            continue
        payload = line[3:]
        if " -> " in payload:
            old_p, new_p = payload.split(" -> ", 1)
            touched.add(_unquote_git_path(old_p))
            touched.add(_unquote_git_path(new_p))
        else:
            touched.add(_unquote_git_path(payload))

    diff = subprocess.run(
        ["git", "-C", str(repo), "diff", "--name-only", base_ref],
        capture_output=True,
        text=True,
    )
    if diff.returncode != 0:
        return False, f"git diff --name-only {base_ref} failed: {diff.stderr.strip()}"
    for line in diff.stdout.splitlines():
        path_str = _unquote_git_path(line)
        if path_str:
            touched.add(path_str)

    disallowed = sorted(
        path_str
        for path_str in touched
        if not any(fnmatch.fnmatch(path_str, glob) for glob in allowed_globs)
    )
    if disallowed:
        return False, f"out-of-scope writes: {', '.join(disallowed)}"
    return True, f"all {len(touched)} touched path(s) within allowed scope"


def run_unittest(repo: Path, start_dir: str = "tests", timeout: float = 60.0) -> tuple[bool, str]:
    """Run stdlib unittest discovery inside `repo`."""
    if not (repo / start_dir).exists():
        return False, f"test directory missing: {start_dir}"
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "discover", "-s", start_dir],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, f"unittest timed out after {timeout:g}s"
    output = (proc.stdout + "\n" + proc.stderr).strip()
    if proc.returncode != 0:
        return False, output or f"unittest exited {proc.returncode}"
    last_line = output.splitlines()[-1] if output else "OK"
    return True, last_line


def check_mutation_caught(
    repo: Path,
    rel_file: str,
    mutator: Callable[[str], str],
    test_cmd: list[str] | None = None,
) -> tuple[bool, str]:
    """Re-inject a bug via `mutator`, verify tests fail, and unconditionally restore the original file."""
    target = repo / rel_file
    if not target.is_file():
        return False, f"mutation target missing: {rel_file}"
    orig = target.read_text(encoding="utf-8")
    mutated = mutator(orig)
    if not isinstance(mutated, str) or mutated == orig:
        return False, f"mutator made no change to {rel_file}"

    cmd = list(test_cmd) if test_cmd is not None else [
        sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests",
    ]
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        target.write_text(mutated, encoding="utf-8")
        try:
            proc = subprocess.run(cmd, cwd=repo, env=env, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            return True, f"mutation in {rel_file} caught via test timeout"
        if proc.returncode != 0:
            return True, f"mutation in {rel_file} caught by tests (exit {proc.returncode})"
        return False, f"mutation in {rel_file} survived tests (exit 0)"
    finally:
        target.write_text(orig, encoding="utf-8")


def load_events_from_env() -> list[dict[str, Any]]:
    """Read structured harness events JSON from `ASTACK_EVAL_EVENTS_JSON` if set and readable."""
    raw_path = os.environ.get("ASTACK_EVAL_EVENTS_JSON", "").strip()
    if not raw_path:
        return []
    path = Path(raw_path)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def final_text_from_env() -> str:
    """Return the agent's final response text passed via `ASTACK_EVAL_FINAL_TEXT`."""
    return os.environ.get("ASTACK_EVAL_FINAL_TEXT", "")


def astack_home_from_env(ws: Path) -> Path:
    """Resolve isolated `ASTACK_HOME` for an eval workspace."""
    env_home = os.environ.get("ASTACK_HOME", "").strip()
    if env_home:
        return Path(env_home)
    prog_home = ws / "program" / "astack_home"
    if prog_home.is_dir():
        return prog_home
    return ws / ".astack-home"


def report_and_exit(checks: list[tuple[str, bool, str]]) -> int:
    """Print `[PASS]` / `[FAIL]` per check and return 0 iff all checks passed else 1."""
    all_ok = True
    for name, ok, detail in checks:
        tag = "PASS" if ok else "FAIL"
        print(f"[{tag}] {name}: {detail}")
        if not ok:
            all_ok = False
    return 0 if all_ok else 1


def _prepare_oracle_workspace(case_dir: Path, ws: Path) -> tuple[bool, str]:
    for child in sorted(case_dir.iterdir()):
        if child.is_dir() and child.name not in ("graders", "__pycache__"):
            shutil.copytree(child, ws / child.name, dirs_exist_ok=True)
    setup_script = case_dir / "setup.sh"
    if setup_script.is_file():
        try:
            proc = subprocess.run(
                ["bash", str(setup_script)],
                cwd=ws,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            return False, "setup.sh timed out after 60s"
        if proc.returncode != 0:
            return False, f"setup.sh failed (exit {proc.returncode}): {proc.stderr.strip()}"
    return True, "ok"


def _build_isolated_verify_env(ws: Path, hook_result: Any) -> dict[str, str]:
    astack_home = (ws / "program" / "astack_home") if (ws / "program" / "astack_home").is_dir() else (ws / ".astack-home")
    astack_home.mkdir(parents=True, exist_ok=True)
    astack_state = ws / ".astack-state"
    astack_state.mkdir(parents=True, exist_ok=True)
    dispatch_state = ws / ".astack-dispatches"
    dispatch_state.mkdir(parents=True, exist_ok=True)
    xdg_cache = ws / ".xdg-cache"
    xdg_cache.mkdir(parents=True, exist_ok=True)

    final_text = ""
    events: list[Any] = []
    if isinstance(hook_result, dict):
        final_text = str(hook_result.get("final_text", ""))
        raw_events = hook_result.get("events", [])
        if isinstance(raw_events, list):
            events = raw_events

    events_path = ws / ".astack-eval-events.json"
    events_path.write_text(json.dumps(events, indent=2), encoding="utf-8")

    return {
        **os.environ,
        "ASTACK_HOME": str(astack_home),
        "ASTACK_STATE_DIR": str(astack_state),
        "ASTACK_DISPATCH_STATE_DIR": str(dispatch_state),
        "XDG_CACHE_HOME": str(xdg_cache),
        "ASTACK_EVAL_FINAL_TEXT": final_text,
        "ASTACK_EVAL_EVENTS_JSON": str(events_path),
    }


def run_oracle_check(case_dir: Path, oracle_path: Path) -> tuple[bool, str]:
    """Run RED then GREEN offline verification for one eval case using its separated oracle module."""
    verify_script = case_dir / "verify.py"
    if not verify_script.is_file():
        return False, f"{case_dir.name}: missing verify.py"
    if not oracle_path.is_file():
        return False, f"{case_dir.name}: missing oracle {oracle_path}"

    spec = importlib.util.spec_from_file_location(f"astack_eval_oracle_{oracle_path.stem}", oracle_path)
    if spec is None or spec.loader is None:
        return False, f"{case_dir.name}: could not load oracle module {oracle_path}"
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)

    apply_fn = getattr(oracle, "apply", None)
    if not callable(apply_fn):
        return False, f"{case_dir.name}: oracle {oracle_path.name} missing callable apply(ws)"
    violate_fn = getattr(oracle, "violate", None)

    # Phase 1: RED (untouched scaffold or explicit violation MUST fail verify.py)
    with tempfile.TemporaryDirectory(prefix=f"astack-oracle-red-{case_dir.name}-") as td_red:
        ws_red = Path(td_red)
        ok_prep, prep_msg = _prepare_oracle_workspace(case_dir, ws_red)
        if not ok_prep:
            return False, f"{case_dir.name} RED: {prep_msg}"
        red_meta = violate_fn(ws_red) if callable(violate_fn) else None
        red_env = _build_isolated_verify_env(ws_red, red_meta)
        try:
            red_proc = subprocess.run(
                [sys.executable, "-B", str(verify_script), str(ws_red)],
                cwd=ws_red,
                env=red_env,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            return False, f"{case_dir.name} RED: verify.py timed out after 60s"
        if red_proc.returncode == 0:
            out_preview = (red_proc.stdout.strip() or red_proc.stderr.strip())[:200]
            return False, f"{case_dir.name} RED unexpectedly exited 0: {out_preview}"

    # Phase 2: GREEN (oracle.apply(ws) MUST pass verify.py with exit 0)
    with tempfile.TemporaryDirectory(prefix=f"astack-oracle-green-{case_dir.name}-") as td_green:
        ws_green = Path(td_green)
        ok_prep, prep_msg = _prepare_oracle_workspace(case_dir, ws_green)
        if not ok_prep:
            return False, f"{case_dir.name} GREEN: {prep_msg}"
        green_meta = apply_fn(ws_green)
        green_env = _build_isolated_verify_env(ws_green, green_meta)
        try:
            green_proc = subprocess.run(
                [sys.executable, "-B", str(verify_script), str(ws_green)],
                cwd=ws_green,
                env=green_env,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            return False, f"{case_dir.name} GREEN: verify.py timed out after 60s"
        if green_proc.returncode != 0:
            err_preview = (green_proc.stdout.strip() + "\n" + green_proc.stderr.strip()).strip()[:300]
            return False, f"{case_dir.name} GREEN failed (exit {green_proc.returncode}): {err_preview}"

    return True, f"{case_dir.name}: RED (exit {red_proc.returncode}) -> GREEN (exit 0)"
