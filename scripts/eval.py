#!/usr/bin/env python3
"""Multi-harness eval runner for astack.

Runs evals/* against Claude Code (`claude`), Codex (`codex`), Antigravity (`agy`),
Cursor CLI (`cursor`), Devin (`devin`), or Pi (`pi`) with isolated harness mounting,
cross-harness reviewer_pool support, canonical tool-call + astack-dispatch receipt
extraction, and deterministic + optional LLM grading.

Usage:
  python3 scripts/eval.py --harness codex --case "vectored-review-*"
  python3 scripts/eval.py --harness agy --case "rule-*" --judge-harness none
  python3 scripts/eval.py --harness claude --case "vectored-review-cross-harness"
  python3 scripts/eval.py --harness codex --case "vectored-review-cross-harness" \
      --reviewer-pool '[{"provider":"openai","model":"gpt-5.4-mini","harness":"codex"},{"provider":"anthropic","model":"sonnet","harness":"claude"}]'
"""
from __future__ import annotations

import argparse
import concurrent.futures
import fnmatch
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
EVALS_DIR = ROOT / "evals"
HARNESS_DIR = ROOT / "harness"
BIN_DIR = ROOT / "bin"
ORACLES_DIR = ROOT / "tests" / "fixtures" / "eval_oracles"

if str(EVALS_DIR) not in sys.path:
    sys.path.insert(0, str(EVALS_DIR))
import _eval_kit

SUPPORTED_HARNESSES = ("claude", "codex", "agy", "cursor", "devin", "pi")

HARNESS_PACKAGE = {
    "claude": "claude-code",
    "codex": "codex",
    "agy": "antigravity",
    "cursor": "cursor",
    "devin": "portable",
    "pi": "portable",
}

HARNESS_BINARIES = {
    "claude": ("claude",),
    "codex": ("codex",),
    "agy": ("agy", "antigravity"),
    "cursor": ("cursor-agent", "agent"),
    "devin": ("devin",),
    "pi": ("pi",),
}

# Default native 2-model pools used when adapting single-vendor vectored-review cases to non-Claude harnesses.
DEFAULT_HARNESS_SETTINGS: dict[str, dict[str, Any]] = {
    "codex": {
        "roles": {"worker": {"provider": "openai", "model": "gpt-5.4-mini", "effort": "medium"}},
        "reviewer_pool": [
            {"provider": "openai", "model": "gpt-5.4", "effort": "medium", "harness": "codex"},
            {"provider": "openai", "model": "gpt-5.4-mini", "effort": "medium", "harness": "codex"},
        ],
    },
    "agy": {
        "roles": {"worker": {"provider": "google", "model": "gemini-2.5-flash", "effort": "medium"}},
        "reviewer_pool": [
            {"provider": "google", "model": "gemini-2.5-pro", "effort": "medium", "harness": "agy"},
            {"provider": "google", "model": "gemini-2.5-flash", "effort": "medium", "harness": "agy"},
        ],
    },
    "cursor": {
        "roles": {"worker": {"provider": "cursor", "model": "gpt-4.1-mini", "effort": "medium"}},
        "reviewer_pool": [
            {"provider": "cursor", "model": "sonnet-4", "effort": "medium", "harness": "cursor"},
            {"provider": "cursor", "model": "gpt-4.1-mini", "effort": "medium", "harness": "cursor"},
        ],
    },
    "devin": {
        "roles": {"worker": {"provider": "devin", "model": "haiku", "effort": "medium"}},
        "reviewer_pool": [
            {"provider": "devin", "model": "sonnet", "effort": "medium", "harness": "devin"},
            {"provider": "devin", "model": "haiku", "effort": "medium", "harness": "devin"},
        ],
    },
    "pi": {
        "roles": {"worker": {"provider": "openai", "model": "gpt-5.4-mini", "effort": "medium"}},
        "reviewer_pool": [
            {"provider": "anthropic", "model": "claude-sonnet-4-6", "effort": "medium", "harness": "pi"},
            {"provider": "openai", "model": "gpt-5.4-mini", "effort": "medium", "harness": "pi"},
        ],
    },
}


def _detect_codex_default_model() -> str:
    cfg = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex")).expanduser() / "config.toml"
    try:
        if cfg.is_file():
            m = re.search(r'^\s*model\s*=\s*"([^"]+)"', cfg.read_text(encoding="utf-8"), re.M)
            if m:
                return m.group(1).strip()
    except OSError:
        pass
    return "default"


def _default_settings_for_harness(harness: str) -> dict[str, Any] | None:
    if harness == "codex":
        mod = _detect_codex_default_model()
        return {
            "roles": {"worker": {"provider": "anthropic", "model": "haiku", "effort": "medium"}},
            "reviewer_pool": [
                {"provider": "openai", "model": mod, "effort": "medium", "harness": "codex"},
                {"provider": "anthropic", "model": "haiku", "effort": "medium", "harness": "claude"},
            ],
        }
    return DEFAULT_HARNESS_SETTINGS.get(harness)


def split_front_matter(text: str) -> tuple[dict[str, str], str]:
    match = re.match(r"---\n(.*?)\n---\n?", text, re.S)
    if not match:
        return {}, text
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        fields[key.strip()] = val.strip()
    return fields, text[match.end():]


def _unquote(val: str) -> str:
    val = val.strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
        return val[1:-1]
    return val


def slugify_reviewer(entry: dict[str, Any]) -> str:
    parts = [entry.get("provider", ""), entry.get("model", ""), entry.get("effort", "")]
    raw = "-".join(p for p in parts if p).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return slug or "default"


def find_harness_binary(harness: str) -> str | None:
    for name in HARNESS_BINARIES[harness]:
        if found := shutil.which(name):
            return found
    for directory in (
        Path.home() / ".local" / "bin",
        Path("/opt/homebrew/bin"),
        Path("/usr/local/bin"),
    ):
        for name in HARNESS_BINARIES[harness]:
            candidate = directory / name
            try:
                if candidate.is_file() and os.access(candidate, os.X_OK):
                    return str(candidate)
            except OSError:
                continue
    return None


def parse_case_meta(case_dir: Path) -> dict[str, Any]:
    """Parse case.yaml metadata for an eval case directory."""
    meta = _eval_kit.parse_case_yaml(case_dir / "case.yaml")
    if not meta.get("name"):
        meta["name"] = case_dir.name
    return meta


def _normalize_skill_tokens(
    skill: str | None = None,
    skills_filter: list[str] | tuple[str, ...] | set[str] | None = None,
) -> set[str]:
    wanted: set[str] = set()
    if skill:
        for part in skill.split(","):
            tok = part.strip()
            if tok:
                wanted.add(tok)
    if skills_filter:
        for entry in skills_filter:
            for part in str(entry).split(","):
                tok = part.strip()
                if tok:
                    wanted.add(tok)
    return wanted


def discover_cases(
    pattern: str | None = "*",
    *,
    tier: str | None = None,
    kind: str | None = None,
    skill: str | None = None,
    skills_filter: list[str] | tuple[str, ...] | set[str] | None = None,
) -> list[Path]:
    """Discover eval cases filtered by glob(s), cumulative tier, exact kind, and/or skill overlap."""
    if tier is not None and tier != "" and tier not in _eval_kit.TIER_ORDER:
        raise ValueError(f"invalid tier {tier!r}; expected one of {_eval_kit.VALID_TIERS}")
    if kind is not None and kind != "" and kind not in _eval_kit.VALID_KINDS:
        raise ValueError(f"invalid kind {kind!r}; expected one of {_eval_kit.VALID_KINDS}")

    if pattern is None:
        patterns = ["*"]
    else:
        patterns = [p.strip() for p in pattern.split(",") if p.strip()]
        if not patterns:
            return []
    max_tier_rank = _eval_kit.TIER_ORDER[tier] if tier else None
    wanted_skills = _normalize_skill_tokens(skill=skill, skills_filter=skills_filter)

    cases = sorted(p for p in EVALS_DIR.iterdir() if p.is_dir() and (p / "case.yaml").is_file())
    matched: list[Path] = []
    for case_dir in cases:
        if not any(fnmatch.fnmatch(case_dir.name, pat) for pat in patterns):
            continue
        if max_tier_rank is None and not kind and not wanted_skills:
            matched.append(case_dir)
            continue
        meta = parse_case_meta(case_dir)
        if max_tier_rank is not None:
            case_rank = _eval_kit.TIER_ORDER.get(meta.get("tier", ""))
            if case_rank is None or case_rank > max_tier_rank:
                continue
        if kind and meta.get("kind") != kind:
            continue
        if wanted_skills and not (set(meta.get("skills", [])) & wanted_skills):
            continue
        matched.append(case_dir)
    return matched


def select_cases_from_diff(
    base_ref: str,
    *,
    changed_files: list[str] | None = None,
) -> list[Path]:
    """Select eval cases impacted by git diff against `base_ref` (or an explicit `changed_files` list)."""
    if changed_files is None:
        proc = subprocess.run(
            ["git", "-C", str(ROOT), "diff", "--name-only", f"{base_ref}...HEAD"],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            proc = subprocess.run(
                ["git", "-C", str(ROOT), "diff", "--name-only", "HEAD"],
                capture_output=True,
                text=True,
            )
        files = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    else:
        files = [str(f).strip() for f in changed_files if str(f).strip()]

    selected: set[Path] = set()
    touched_skills: set[str] = set()
    include_smoke = False

    for raw_path in files:
        rel = raw_path
        while rel.startswith("./"):
            rel = rel[2:]
        rel = rel.lstrip("/")
        parts = rel.split("/")
        if rel in ("scripts/eval.py", "scripts/build.py", "evals/_eval_kit.py", "evals/_repro_verify.py", "hooks.json"):
            include_smoke = True
        elif parts and parts[0] in ("bin", "lib", "agents", "hooks"):
            include_smoke = True
        elif len(parts) >= 2 and parts[0] == "skills":
            touched_skills.add(parts[1])
        elif len(parts) >= 2 and parts[0] == "evals":
            cand = EVALS_DIR / parts[1]
            if cand.is_dir() and (cand / "case.yaml").is_file():
                selected.add(cand)

    if touched_skills:
        selected.update(discover_cases(skills_filter=touched_skills))
    if include_smoke:
        selected.update(discover_cases(tier="smoke"))

    return sorted(selected, key=lambda p: p.name)


def adapt_prompt(prompt_body: str, harness: str, settings: dict[str, Any] | None = None) -> str:
    text = prompt_body.strip()
    if harness == "codex":
        text = text.replace("`/astack:go`", "`$astack-go`").replace("/astack:go", "$astack-go")
    elif harness == "cursor":
        text = text.replace("`/astack:go`", "`/astack-go`").replace("/astack:go", "/astack-go")
    elif harness == "agy":
        text = text.replace(
            "`/astack:go`",
            "Follow the astack-go skill at `.agents/plugins/astack/skills/astack-go/SKILL.md`.",
        )
    elif harness in ("devin", "pi"):
        text = text.replace(
            "`/astack:go`",
            "Follow the astack-go skill at `.agents/skills/astack-go/SKILL.md`.",
        )

    if settings:
        worker = (settings.get("roles") or {}).get("worker")
        if isinstance(worker, dict) and worker.get("provider") and worker.get("model"):
            worker_label = f"{worker['provider']}/{worker['model']}"
            text = re.sub(
                r"The worker built this change on `[^`]+`",
                f"The worker built this change on `{worker_label}`",
                text,
            )
    return text


def mount_harness_into_workspace(
    harness: str,
    workspace: Path,
    settings: dict[str, Any] | None = None,
) -> tuple[dict[str, str], list[str]]:
    """Mount the harness-appropriate package in an isolated workspace. Returns (env_overrides, extra_cli_args)."""
    pkg_dir = HARNESS_DIR / HARNESS_PACKAGE[harness]
    bin_dir = pkg_dir / "bin" if (pkg_dir / "bin").is_dir() else BIN_DIR
    env: dict[str, str] = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
    }
    extra_args: list[str] = []

    if harness == "claude":
        extra_args = ["--plugin-dir", str(pkg_dir)]
    elif harness == "codex":
        codex_home = workspace / ".codex_home"
        codex_home.mkdir(parents=True, exist_ok=True)
        shutil.copytree(pkg_dir / "skills", codex_home / "skills", dirs_exist_ok=True)
        shutil.copytree(pkg_dir / "agents", codex_home / "agents", dirs_exist_ok=True)
        # Preserve auth/config from user's real CODEX_HOME without writing back to it
        real_home = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))
        for fname in ("auth.json", "config.toml"):
            src = real_home / fname
            try:
                if src.is_file():
                    shutil.copy2(src, codex_home / fname)
            except OSError:
                continue
        # Install per-model astack-reviewer-<slug>.toml for every OpenAI/Codex entry in settings.json
        if settings and isinstance(settings.get("reviewer_pool"), list):
            tmpl_path = codex_home / "agents" / "astack-reviewer.toml"
            if tmpl_path.is_file():
                tmpl = tmpl_path.read_text(encoding="utf-8")
                installed_any = False
                seen_slugs: set[str] = set()
                for entry in settings["reviewer_pool"]:
                    if not isinstance(entry, dict):
                        continue
                    ent_harness = (entry.get("harness") or "").lower()
                    prov = (entry.get("provider") or "").lower()
                    if ent_harness and ent_harness != "codex":
                        continue
                    if not ent_harness and prov != "openai":
                        continue
                    slug = slugify_reviewer(entry)
                    base_slug = slug
                    idx = 2
                    while slug in seen_slugs:
                        slug = f"{base_slug}-{idx}"
                        idx += 1
                    seen_slugs.add(slug)
                    body = tmpl.replace('name = "astack-reviewer"', f'name = "astack-reviewer-{slug}"', 1)
                    inject = f'model = "{entry["model"]}"\n'
                    if entry.get("effort"):
                        inject += f'model_reasoning_effort = "{entry["effort"]}"\n'
                    body = body.replace("developer_instructions = ", inject + "developer_instructions = ", 1)
                    (codex_home / "agents" / f"astack-reviewer-{slug}.toml").write_text(body, encoding="utf-8")
                    installed_any = True
                if installed_any:
                    tmpl_path.unlink()
        env["CODEX_HOME"] = str(codex_home)
    elif harness == "agy":
        plugin_dst = workspace / ".agents" / "plugins" / "astack"
        plugin_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(pkg_dir, plugin_dst, dirs_exist_ok=True)
    elif harness == "cursor":
        cur_dir = workspace / ".cursor"
        shutil.copytree(pkg_dir / "skills", cur_dir / "skills", dirs_exist_ok=True)
        shutil.copytree(pkg_dir / "agents", cur_dir / "agents", dirs_exist_ok=True)
    elif harness in ("devin", "pi"):
        ag_dir = workspace / ".agents"
        shutil.copytree(pkg_dir / "skills", ag_dir / "skills", dirs_exist_ok=True)
        shutil.copytree(pkg_dir / "agents", ag_dir / "agents", dirs_exist_ok=True)

    return env, extra_args


def build_eval_command(
    harness: str,
    binary: str,
    prompt_text: str,
    workspace: Path,
    *,
    extra_args: list[str] | None = None,
    model: str = "",
    effort: str = "",
) -> tuple[list[str], str | None]:
    extra = list(extra_args or [])
    if harness == "claude":
        argv = [
            binary,
            "-p",
            "--output-format",
            "stream-json",
            "--verbose",
            "--no-session-persistence",
            "--permission-mode",
            "bypassPermissions",
            *extra,
        ]
        if model:
            argv.extend(["--model", model])
        if effort:
            argv.extend(["--effort", effort])
        return argv, prompt_text

    if harness == "codex":
        argv = [
            binary,
            "exec",
            "--json",
            "--skip-git-repo-check",
            "--dangerously-bypass-approvals-and-sandbox",
            "-C",
            str(workspace),
        ]
        if model:
            argv.extend(["--model", model])
        if effort:
            argv.extend(["-c", f'model_reasoning_effort="{effort}"'])
        argv.append("-")
        return argv, prompt_text

    if harness == "agy":
        argv = [
            binary,
            "-p",
            prompt_text,
            "--output-format",
            "stream-json",
            "--dangerously-skip-permissions",
        ]
        if model:
            argv.extend(["--model", model])
        if effort:
            argv.extend(["--effort", effort])
        return argv, None

    if harness == "cursor":
        argv = [binary, "-p", "--trust", "--force", "--output-format", "stream-json"]
        if model:
            argv.extend(["--model", model])
        argv.append(prompt_text)
        return argv, None

    if harness == "devin":
        argv = [
            binary,
            "--respect-workspace-trust",
            "false",
            "--permission-mode",
            "autonomous",
            "--sandbox",
        ]
        if model:
            argv.extend(["--model", model])
        argv.extend(["-p", "--", prompt_text])
        return argv, None

    if harness == "pi":
        argv = [binary, "-p", "--mode", "json"]
        if model:
            if "/" in model:
                prov, mod = model.split("/", 1)
                argv.extend(["--provider", prov, "--model", mod])
            else:
                argv.extend(["--model", model])
        if effort:
            argv.extend(["--thinking", effort])
        argv.append(prompt_text)
        return argv, None

    raise ValueError(f"unsupported harness: {harness}")


def _extract_dispatch_from_command(cmd: str) -> list[dict[str, Any]]:
    """Extract canonical spawn events from `astack-dispatch run ...` shell invocations."""
    events: list[dict[str, Any]] = []
    if "astack-dispatch" not in cmd or " run" not in cmd:
        return events
    # Split shell pipelines / chains roughly so multi-command lines still parse each dispatch call
    segments = re.split(r"(?:&&|\|\||;|\n)", cmd)
    for seg in segments:
        if "astack-dispatch" not in seg:
            continue
        try:
            tokens = shlex.split(seg)
        except ValueError:
            tokens = seg.split()
        idx = next((i for i, t in enumerate(tokens) if Path(t).name == "astack-dispatch"), None)
        if idx is None or idx + 1 >= len(tokens) or tokens[idx + 1] != "run":
            continue
        provider = model = harness = role = ""
        role = "reviewer"
        i = idx + 2
        while i < len(tokens):
            tok = tokens[i]
            nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
            if tok == "--provider" and nxt:
                provider = nxt
                i += 2
            elif tok.startswith("--provider="):
                provider = tok.split("=", 1)[1]
                i += 1
            elif tok == "--model" and nxt:
                model = nxt
                i += 2
            elif tok.startswith("--model="):
                model = tok.split("=", 1)[1]
                i += 1
            elif tok == "--harness" and nxt:
                harness = nxt
                i += 2
            elif tok.startswith("--harness="):
                harness = tok.split("=", 1)[1]
                i += 1
            elif tok == "--role" and nxt:
                role = nxt
                i += 2
            elif tok.startswith("--role="):
                role = tok.split("=", 1)[1]
                i += 1
            else:
                i += 1
        if model or provider:
            events.append(
                {
                    "kind": "spawn",
                    "role": role,
                    "provider": provider,
                    "model": model,
                    "harness": harness,
                    "via": "astack-dispatch",
                    "raw_tool": "Bash",
                    "raw_input": json.dumps(
                        {"subagent_type": f"astack:{role}", "provider": provider, "model": model, "harness": harness}
                    ),
                }
            )
    return events


_SKILLS_GET_RE = re.compile(
    r"""(?:^|[\s;|&("'`])(?:[^\s;|&("'`]*/)?astack-tools\s+skills\s+get\s+(?:"([^"]+)"|'([^']+)'|([^\s;|&)'"`]+))"""
)
_SKILL_MD_PATH_RE = re.compile(r"([A-Za-z0-9_./~-]+SKILL\.md)")
_SKILL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _extract_skill_reads_from_shell(cmd: str) -> list[str]:
    """Extract canonical SKILL.md targets from shell commands (`astack-tools skills get` or explicit paths)."""
    if not cmd:
        return []
    targets: list[str] = []
    seen: set[str] = set()

    norm_cmd = cmd.replace('\\"', '"').replace("\\'", "'")
    for m in _SKILLS_GET_RE.finditer(norm_cmd):
        raw_name = (m.group(1) or m.group(2) or m.group(3) or "").strip()
        name = (
            raw_name.strip("'\"")
            .removeprefix("/astack:")
            .removeprefix("$astack-")
            .removeprefix("astack-")
            .strip()
        )
        if name and _SKILL_NAME_RE.fullmatch(name):
            target = f"skills/{name}/SKILL.md"
            if target not in seen:
                seen.add(target)
                targets.append(target)

    for m in _SKILL_MD_PATH_RE.finditer(cmd):
        target = m.group(1)
        if target not in seen:
            seen.add(target)
            targets.append(target)

    return targets


def _classify_agent_role(agent_type: str) -> str:
    low = (agent_type or "").lower()
    if "reviewer" in low:
        return "reviewer"
    if "worker" in low:
        return "worker"
    if "general" in low:
        return "general"
    return low or "unknown"


def _infer_model_from_codex_agent_type(agent_type: str, settings: dict[str, Any] | None) -> tuple[str, str]:
    """Match astack-reviewer-<slug> back to (provider, model) from settings.json."""
    if not settings or not isinstance(settings.get("reviewer_pool"), list):
        return "", ""
    low = agent_type.lower()
    for entry in settings["reviewer_pool"]:
        if isinstance(entry, dict) and slugify_reviewer(entry) in low:
            return str(entry.get("provider", "")), str(entry.get("model", ""))
    return "", ""


def parse_harness_events(
    harness: str,
    raw_stdout: str,
    workspace: Path | None = None,
    settings: dict[str, Any] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Parse structured stdout from any supported harness plus disk dispatch receipts into (final_text, events)."""
    events: list[dict[str, Any]] = []
    text_chunks: list[str] = []
    final_result_text: str | None = None

    for line in raw_stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not stripped.startswith("{"):
            text_chunks.append(line)
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            text_chunks.append(line)
            continue
        if not isinstance(obj, dict):
            continue

        etype = str(obj.get("type", ""))
        ag_event = str(obj.get("event", ""))

        # --- Antigravity (`agy`) real stream-json events ---
        if ag_event == "result" and isinstance(obj.get("result"), dict):
            resp = obj["result"].get("response")
            if isinstance(resp, str):
                final_result_text = resp
            continue
        if ag_event == "step_update" and isinstance(obj.get("step_update"), dict):
            su = obj["step_update"]
            st = str(su.get("step_type", ""))
            state = str(su.get("state", ""))
            if st == "tool" and state == "DONE":
                tinfo = su.get("tool_info") or {}
                tname = str(su.get("tool_name") or tinfo.get("name") or "")
                params = tinfo.get("parameters") or {}
                if not isinstance(params, dict):
                    params = {"raw": str(params)}
                params_json = json.dumps(params)
                low = tname.lower()
                if low in ("read_file", "view_file", "read"):
                    target = str(params.get("Path") or params.get("AbsolutePath") or params.get("path") or params.get("file_path") or "")
                    events.append({"kind": "read", "target": target, "raw_tool": tname, "raw_input": params_json})
                elif low in ("run_command", "bash", "shell"):
                    cmd = str(params.get("CommandLine") or params.get("command") or "")
                    events.append({"kind": "shell", "command": cmd, "raw_tool": tname, "raw_input": params_json})
                    events.extend(_extract_dispatch_from_command(cmd))
                    for target in _extract_skill_reads_from_shell(cmd):
                        events.append({"kind": "read", "target": target, "raw_tool": tname, "raw_input": cmd})
                elif low in ("invoke_subagent", "spawn_agent"):
                    role_str = str(params.get("TypeName") or params.get("Role") or "")
                    model_str = str(params.get("Model") or "")
                    events.append(
                        {
                            "kind": "spawn",
                            "role": _classify_agent_role(role_str),
                            "provider": "",
                            "model": model_str,
                            "harness": "agy",
                            "via": "native",
                            "raw_tool": tname,
                            "raw_input": params_json,
                        }
                    )
                else:
                    events.append({"kind": "other", "raw_tool": tname, "raw_input": params_json})
            continue

        # --- Error events (Codex / Claude / Pi) ---
        if etype in ("error", "turn.failed"):
            err_msg = obj.get("message") or (obj.get("error") or {}).get("message") or str(obj)
            events.append({"kind": "error", "message": str(err_msg), "raw_tool": etype, "raw_input": json.dumps(obj)})
            continue

        # --- Claude Code stream-json ---
        if etype == "result" and isinstance(obj.get("result"), str):
            final_result_text = obj["result"]
        elif etype == "assistant" and isinstance(obj.get("message"), dict):
            for block in obj["message"].get("content", []) or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text" and isinstance(block.get("text"), str):
                    text_chunks.append(block["text"])
                elif block.get("type") == "tool_use":
                    tname = str(block.get("name", ""))
                    tinput = block.get("input") or {}
                    tinput_json = json.dumps(tinput)
                    if tname == "Read":
                        events.append({"kind": "read", "target": str(tinput.get("file_path", "")), "raw_tool": tname, "raw_input": tinput_json})
                    elif tname == "Bash":
                        cmd = str(tinput.get("command", ""))
                        events.append({"kind": "shell", "command": cmd, "raw_tool": tname, "raw_input": tinput_json})
                        events.extend(_extract_dispatch_from_command(cmd))
                        for target in _extract_skill_reads_from_shell(cmd):
                            events.append({"kind": "read", "target": target, "raw_tool": tname, "raw_input": cmd})
                    elif tname == "Agent":
                        st = str(tinput.get("subagent_type", ""))
                        events.append(
                            {
                                "kind": "spawn",
                                "role": _classify_agent_role(st),
                                "provider": "anthropic",
                                "model": str(tinput.get("model", "")),
                                "harness": "claude",
                                "via": "native",
                                "raw_tool": tname,
                                "raw_input": tinput_json,
                            }
                        )
                    else:
                        events.append({"kind": "other", "raw_tool": tname, "raw_input": tinput_json})

        # --- Codex exec --json JSONL ---
        elif etype in ("item.completed", "item.started") and isinstance(obj.get("item"), dict):
            item = obj["item"]
            itype = str(item.get("type", ""))
            if itype == "agent_message" and etype == "item.completed" and isinstance(item.get("text"), str):
                final_result_text = item["text"]
                text_chunks.append(item["text"])
            elif itype == "command_execution" and etype == "item.completed":
                cmd = str(item.get("command", ""))
                events.append({"kind": "shell", "command": cmd, "raw_tool": "Bash", "raw_input": json.dumps({"command": cmd})})
                events.extend(_extract_dispatch_from_command(cmd))
                for target in _extract_skill_reads_from_shell(cmd):
                    events.append({"kind": "read", "target": target, "raw_tool": "Bash", "raw_input": cmd})
            elif itype in ("collab_tool_call", "subagent_call") and etype == "item.completed":
                tool = str(item.get("tool", ""))
                if tool in ("spawn_agent", ""):
                    atype = str(item.get("agent_type") or (item.get("arguments") or {}).get("agent_type") or "")
                    prov, mod = _infer_model_from_codex_agent_type(atype, settings)
                    events.append(
                        {
                            "kind": "spawn",
                            "role": _classify_agent_role(atype),
                            "provider": prov,
                            "model": mod or str((item.get("arguments") or {}).get("model", "")),
                            "harness": "codex",
                            "via": "native",
                            "raw_tool": "spawn_agent",
                            "raw_input": json.dumps(item),
                        }
                    )

        # --- Antigravity / Cursor / Pi generic JSON event formats ---
        elif etype in ("tool_use", "tool_call", "tool_execution_start"):
            tname = str(obj.get("tool") or obj.get("toolName") or obj.get("name") or "")
            tinput = obj.get("input") or obj.get("args") or obj.get("arguments") or {}
            if not isinstance(tinput, dict):
                tinput = {"raw": str(tinput)}
            tinput_json = json.dumps(tinput)
            low = tname.lower()
            if low in ("read_file", "read", "readtoolcall"):
                target = str(tinput.get("Path") or tinput.get("path") or tinput.get("file_path") or "")
                events.append({"kind": "read", "target": target, "raw_tool": tname, "raw_input": tinput_json})
            elif low in ("run_command", "bash", "shell", "shelltoolcall"):
                cmd = str(tinput.get("CommandLine") or tinput.get("command") or tinput.get("cmd") or "")
                events.append({"kind": "shell", "command": cmd, "raw_tool": tname, "raw_input": tinput_json})
                events.extend(_extract_dispatch_from_command(cmd))
                for target in _extract_skill_reads_from_shell(cmd):
                    events.append({"kind": "read", "target": target, "raw_tool": tname, "raw_input": cmd})
            elif low in ("invoke_subagent", "spawn_agent", "subagent", "agent", "subagenttoolcall"):
                role_str = str(tinput.get("Role") or tinput.get("TypeName") or tinput.get("subagent_type") or tinput.get("agent_type") or "")
                model_str = str(tinput.get("Model") or tinput.get("model") or "")
                events.append(
                    {
                        "kind": "spawn",
                        "role": _classify_agent_role(role_str),
                        "provider": "",
                        "model": model_str,
                        "harness": harness,
                        "via": "native",
                        "raw_tool": tname,
                        "raw_input": tinput_json,
                    }
                )
        elif etype in ("message_end", "final", "turn_end"):
            msg = obj.get("message") or obj.get("text") or obj.get("content")
            if isinstance(msg, str):
                final_result_text = msg
            elif isinstance(msg, dict) and isinstance(msg.get("content"), list):
                parts = [b.get("text", "") for b in msg["content"] if isinstance(b, dict) and b.get("type") == "text"]
                if parts:
                    final_result_text = "\n".join(parts)

    # Also harvest Codex session rollouts under <ws>/.codex_home/sessions/**/*.jsonl (contains exact spawn_agent calls!)
    if harness == "codex" and workspace is not None:
        sessions_dir = workspace / ".codex_home" / "sessions"
        if sessions_dir.is_dir():
            seen_call_ids: set[str] = set()
            for rollout in sorted(sessions_dir.rglob("*.jsonl")):
                try:
                    lines = rollout.read_text(encoding="utf-8", errors="replace").splitlines()
                except OSError:
                    continue
                for rline in lines:
                    if "spawn_agent" not in rline:
                        continue
                    try:
                        rec = json.loads(rline)
                    except json.JSONDecodeError:
                        continue
                    payload = rec.get("payload") if isinstance(rec, dict) else None
                    if not isinstance(payload, dict):
                        continue
                    if payload.get("type") != "function_call" or payload.get("name") != "spawn_agent":
                        continue
                    cid = str(payload.get("id") or "")
                    if cid and cid in seen_call_ids:
                        continue
                    if cid:
                        seen_call_ids.add(cid)
                    args_raw = payload.get("arguments") or "{}"
                    try:
                        fargs = json.loads(args_raw) if isinstance(args_raw, str) else (args_raw if isinstance(args_raw, dict) else {})
                    except json.JSONDecodeError:
                        fargs = {}
                    atype = str(fargs.get("agent_type") or "")
                    prov, mod = _infer_model_from_codex_agent_type(atype, settings)
                    events.append(
                        {
                            "kind": "spawn",
                            "role": _classify_agent_role(atype),
                            "provider": prov,
                            "model": mod or str(fargs.get("model", "")),
                            "harness": "codex",
                            "via": "native",
                            "raw_tool": "spawn_agent",
                            "raw_input": json.dumps({"agent_type": atype, "provider": prov, "model": mod}),
                        }
                    )

    # Also harvest tamper-evident disk receipts written by `astack-dispatch run` (deduplicated against shell commands)
    if workspace is not None and workspace.is_dir():
        existing_dispatch = {
            (e.get("role"), e.get("provider"), e.get("model"), e.get("harness"))
            for e in events
            if e.get("kind") == "spawn" and e.get("via") == "astack-dispatch"
        }
        for receipt_file in sorted(workspace.rglob("*.receipt.json")):
            try:
                rec = json.loads(receipt_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(rec, dict) or not rec.get("model"):
                continue
            sig = (rec.get("role", "reviewer"), rec.get("provider", ""), rec.get("model", ""), rec.get("harness", ""))
            if sig in existing_dispatch:
                continue
            existing_dispatch.add(sig)
            events.append(
                {
                    "kind": "spawn",
                    "role": str(rec.get("role", "reviewer")),
                    "provider": str(rec.get("provider", "")),
                    "model": str(rec.get("model", "")),
                    "harness": str(rec.get("harness", "")),
                    "via": "astack-dispatch",
                    "raw_tool": "astack-dispatch",
                    "raw_input": json.dumps(rec),
                }
            )
            events.append(
                {
                    "kind": "shell",
                    "command": " ".join(rec.get("argv") or ["astack-dispatch", "run"]),
                    "raw_tool": "astack-dispatch",
                    "raw_input": json.dumps(rec),
                }
            )

    final_text = final_result_text if final_result_text is not None else "\n".join(text_chunks)
    return final_text.strip(), events


def _adapt_model_tokens(pattern: str, settings: dict[str, Any] | None) -> str:
    """Substitute default Claude aliases (sonnet/haiku) with the active pool's non-worker / worker models."""
    if not settings:
        return pattern
    worker = (settings.get("roles") or {}).get("worker") or {}
    worker_model = str(worker.get("model", ""))
    pool = settings.get("reviewer_pool") or []
    non_worker = next((str(e["model"]) for e in pool if isinstance(e, dict) and str(e.get("model", "")) != worker_model), "")
    if not worker_model or not non_worker or (worker_model == "haiku" and non_worker == "sonnet"):
        return pattern
    out = pattern.replace("sonnet", re.escape(non_worker))
    out = out.replace("haiku", re.escape(worker_model))
    return out


def evaluate_tool_grader(
    fields: dict[str, str],
    events: list[dict[str, Any]],
    settings: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    tool = _unquote(fields.get("tool", ""))
    raw_pattern = _unquote(fields.get("input_match", ""))
    min_count = int(fields["min"]) if "min" in fields else 1
    max_count = int(fields["max"]) if "max" in fields else None

    adapted_pattern = _adapt_model_tokens(raw_pattern, settings)
    count = 0

    if tool == "Read":
        rx = re.compile(adapted_pattern) if adapted_pattern else None
        for ev in events:
            if ev["kind"] == "read":
                hay = ev.get("target", "") + " " + ev.get("raw_input", "")
                if rx is None or rx.search(hay):
                    count += 1
    elif tool == "Bash":
        rx = re.compile(adapted_pattern) if adapted_pattern else None
        for ev in events:
            if ev["kind"] == "shell":
                hay = ev.get("command", "") + " " + ev.get("raw_input", "")
                if rx is None or rx.search(hay):
                    count += 1
    elif tool == "Agent":
        # Match canonical spawn events across native subagents AND astack-dispatch
        wants_reviewer = "astack:reviewer" in raw_pattern or "reviewer" in raw_pattern
        wants_worker = "astack:worker" in raw_pattern or "worker" in raw_pattern
        wants_general = "general-purpose" in raw_pattern
        # Extract model requirement if the grader binds a model alongside subagent_type
        worker_model = str(((settings or {}).get("roles") or {}).get("worker", {}).get("model", ""))
        pool = (settings or {}).get("reviewer_pool") or []
        non_worker = next((str(e["model"]) for e in pool if isinstance(e, dict) and str(e.get("model", "")) != worker_model), "")
        model_req = ""
        if "sonnet" in raw_pattern:
            model_req = non_worker or "sonnet"
        elif "haiku" in raw_pattern:
            model_req = worker_model or "haiku"

        has_semantic_matcher = wants_reviewer or wants_worker or wants_general or bool(model_req)
        fallback_rx = re.compile(adapted_pattern, re.IGNORECASE) if (raw_pattern and not has_semantic_matcher) else None

        for ev in events:
            if ev["kind"] != "spawn":
                continue
            role = ev.get("role", "")
            mod = ev.get("model", "")
            if fallback_rx is not None:
                haystack = f"{mod} {ev.get('provider', '')} {ev.get('raw_input', '')}"
                if fallback_rx.search(haystack):
                    count += 1
                continue
            if wants_general:
                if role == "general" or "general-purpose" in ev.get("raw_input", ""):
                    count += 1
                continue
            if wants_reviewer and role != "reviewer":
                continue
            if wants_worker and role != "worker":
                continue
            if model_req and model_req.lower() not in (mod or ev.get("raw_input", "")).lower():
                continue
            count += 1
    else:
        rx = re.compile(adapted_pattern) if adapted_pattern else None
        for ev in events:
            if ev.get("raw_tool") == tool and (rx is None or rx.search(ev.get("raw_input", ""))):
                count += 1

    ok = count >= min_count and (max_count is None or count <= max_count)
    bound = f"{min_count}..{max_count if max_count is not None else '∞'}"
    return ok, f"{tool} matched {count}x (expected {bound})"


def evaluate_regex_grader(
    fields: dict[str, str],
    final_text: str,
    settings: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    """Evaluate a regex grader with optional `flags` (`i`, `m`, `s`) and `negate: true`."""
    pat = _adapt_model_tokens(_unquote(fields.get("pattern", "")), settings)
    raw_flags = _unquote(fields.get("flags", "")).lower()
    flags = 0
    if "i" in raw_flags:
        flags |= re.IGNORECASE
    if "m" in raw_flags:
        flags |= re.MULTILINE
    if "s" in raw_flags:
        flags |= re.DOTALL
    negate = _unquote(fields.get("negate", "")).lower() == "true"
    matched = bool(re.search(pat, final_text, flags))
    ok = (not matched) if negate else matched
    if negate:
        detail = f"{'absent (negated)' if ok else 'matched forbidden'} {pat}"
    else:
        detail = f"{'matched' if ok else 'missed'} {pat}"
    return ok, detail


def _workspace_judge_snapshot(workspace: Path | None, max_diff_chars: int = 8000) -> str:
    """Summarize workspace diffs and program artifacts so the LLM judge can grade actual files."""
    if workspace is None or not workspace.is_dir():
        return ""
    sections: list[str] = []
    repo = workspace / "repo"
    if (repo / ".git").exists():
        root_proc = subprocess.run(
            ["git", "-C", str(repo), "rev-list", "--max-parents=0", "HEAD"],
            capture_output=True, text=True,
        )
        base_ref = root_proc.stdout.strip().splitlines()[0] if root_proc.returncode == 0 and root_proc.stdout.strip() else "HEAD"
        st_proc = subprocess.run(["git", "-C", str(repo), "status", "--short"], capture_output=True, text=True)
        diff_proc = subprocess.run(["git", "-C", str(repo), "diff", base_ref], capture_output=True, text=True)
        untracked = [
            ln[3:].strip() for ln in st_proc.stdout.splitlines() if ln.startswith("?? ")
        ]
        parts: list[str] = []
        if st_proc.stdout.strip():
            parts.append(f"git status:\n{st_proc.stdout.strip()}")
        diff_text = diff_proc.stdout.strip()
        if diff_text:
            if len(diff_text) > max_diff_chars:
                diff_text = diff_text[:max_diff_chars] + "\n... [diff truncated]"
            parts.append(f"git diff {base_ref}:\n```diff\n{diff_text}\n```")
        for rel in untracked[:8]:
            fpath = repo / rel
            if fpath.is_file() and fpath.stat().st_size <= 8192:
                try:
                    content = fpath.read_text(encoding="utf-8", errors="replace")[:2000]
                except OSError:
                    continue
                parts.append(f"new file repo/{rel}:\n```\n{content}\n```")
        if parts:
            sections.append("Repository changes (`./repo`):\n" + "\n\n".join(parts))

    prog = workspace / "program"
    if prog.is_dir():
        prog_files = sorted(
            str(p.relative_to(workspace))
            for p in prog.rglob("*")
            if p.is_file() and "dispatch-receipts" not in p.parts
        )[:30]
        if prog_files:
            sections.append("Program / artifact files:\n" + "\n".join(f"- {f}" for f in prog_files))

    if not sections:
        return ""
    return "\n\nWorkspace evidence (read-only snapshot from the run workspace):\n" + "\n\n".join(sections) + "\n"


def run_llm_judge(
    judge_harness: str,
    rubric: str,
    final_text: str,
    settings: dict[str, Any] | None,
    timeout: float = 120.0,
    workspace: Path | None = None,
) -> tuple[bool, str]:
    binary = find_harness_binary(judge_harness)
    if not binary:
        return False, f"judge harness {judge_harness!r} not installed"
    ctx = ""
    if settings:
        ctx = f"\nActive settings.json for this run:\n```json\n{json.dumps(settings, indent=2)}\n```\n"
    ws_snap = _workspace_judge_snapshot(workspace)
    adapted_rubric = _adapt_model_tokens(rubric, settings)
    prompt = (
        "You are grading an agent's final output and workspace artifacts against a strict rubric.\n"
        "You are running read-only in the actual run workspace (when present) and have the workspace diff/artifacts below.\n"
        f"{ctx}{ws_snap}\nRubric:\n{adapted_rubric.strip()}\n\n"
        f"Agent output:\n---\n{final_text}\n---\n\n"
        "Respond with a single line starting with PASS or FAIL followed by a one-sentence reason."
    )
    def _invoke(cwd_path: Path) -> subprocess.CompletedProcess[str]:
        judge_extra: list[str] = []
        if judge_harness == "agy":
            judge_extra = ["--sandbox", "--disable-slash-commands"]
        judge_effort = "low" if judge_harness in ("codex", "claude", "agy") else ""
        argv, stdin_text = build_eval_command(
            judge_harness, binary, prompt, cwd_path, extra_args=judge_extra, effort=judge_effort
        )
        if judge_harness == "codex":
            # Keep judge strictly read-only on the agent workspace
            argv = [
                tok for tok in argv if tok != "--dangerously-bypass-approvals-and-sandbox"
            ]
            if "--sandbox" not in argv and len(argv) >= 2 and argv[1] == "exec":
                argv[2:2] = ["--sandbox", "read-only"]
        return subprocess.run(argv, input=stdin_text, cwd=cwd_path, capture_output=True, text=True, timeout=timeout)

    try:
        if workspace is not None and workspace.is_dir():
            proc = _invoke(workspace)
        else:
            with tempfile.TemporaryDirectory(prefix="astack-judge-") as tmp:
                proc = _invoke(Path(tmp))
    except subprocess.TimeoutExpired:
        return False, "judge timed out"
    judge_text, _ = parse_harness_events(judge_harness, proc.stdout)
    first = next((ln.strip() for ln in judge_text.splitlines() if ln.strip()), "")
    passed = first.upper().startswith("PASS")
    return passed, f"judge({judge_harness}): {first[:140]}"


OUTCOME_GRADER_TYPES = ("command", "llm")
PROCESS_GRADER_TYPES = ("tool_used", "regex", "runtime")


def _extract_token_usage(raw_stdout: str) -> dict[str, int]:
    """Extract token usage totals from harness JSONL streams (Codex turn.completed, Claude result/assistant, generic).

    Prefers aggregate `type == "result"` usage when present (Claude Code emits both per-message
    and aggregate result usage); otherwise sums per-turn `usage` objects (Codex `turn.completed`, etc.).
    """
    result_usage: dict[str, int] | None = None
    summed = {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    def _parse_usage_dict(u: dict[str, Any]) -> dict[str, int]:
        inp = int(u.get("input_tokens") or u.get("prompt_tokens") or 0)
        out = int(u.get("output_tokens") or u.get("completion_tokens") or 0)
        # OpenAI/Codex reports cached_input_tokens as a subset of input_tokens;
        # Anthropic/Claude reports cache_read/cache_creation separately from input_tokens.
        if "cache_read_input_tokens" in u or "cache_creation_input_tokens" in u:
            cache_read = int(u.get("cache_read_input_tokens") or 0)
            cache_create = int(u.get("cache_creation_input_tokens") or 0)
            cached = cache_read + cache_create
            computed_total = inp + cached + out
        else:
            cached = int(u.get("cached_input_tokens") or 0)
            computed_total = inp + out
        explicit_total = int(u.get("total_tokens") or 0)
        return {
            "input_tokens": inp,
            "cached_input_tokens": cached,
            "output_tokens": out,
            "total_tokens": max(explicit_total, computed_total),
        }

    for line in raw_stdout.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        etype = obj.get("type") or obj.get("event")
        if etype == "result" and isinstance(obj.get("usage"), dict):
            result_usage = _parse_usage_dict(obj["usage"])
            continue
        usage_obj: dict[str, Any] | None = None
        if isinstance(obj.get("usage"), dict):
            usage_obj = obj["usage"]
        elif isinstance(obj.get("message"), dict) and isinstance(obj["message"].get("usage"), dict):
            usage_obj = obj["message"]["usage"]
        if usage_obj is not None:
            parsed = _parse_usage_dict(usage_obj)
            for k in summed:
                summed[k] += parsed[k]

    return result_usage if result_usage is not None else summed


def _summarize_scores(results: list[dict[str, Any]]) -> tuple[float, float | None, float | None]:
    """Return `(combined_score, outcome_score, process_score)` across scored graders.

    Outcome graders (`command`, `llm`) measure task results independently of plugin instrumentation;
    process graders (`tool_used`, `regex`, `runtime`) check workflow compliance and hygiene.
    """
    scored = [r for r in results if r["passed"] is not None]
    combined = round(sum(1 for r in scored if r["passed"]) / len(scored), 2) if scored else 0.0
    out_scored = [r for r in scored if r.get("type") in OUTCOME_GRADER_TYPES]
    proc_scored = [r for r in scored if r.get("type") in PROCESS_GRADER_TYPES]
    outcome = round(sum(1 for r in out_scored if r["passed"]) / len(out_scored), 2) if out_scored else None
    process = round(sum(1 for r in proc_scored if r["passed"]) / len(proc_scored), 2) if proc_scored else None
    return combined, outcome, process


def _build_trial_isolation_env(ws: Path) -> dict[str, str]:
    """Create and return per-trial isolated state/cache directory env overrides."""
    astack_home = (ws / "program" / "astack_home") if (ws / "program" / "astack_home").is_dir() else (ws / ".astack-home")
    astack_home.mkdir(parents=True, exist_ok=True)
    astack_state = ws / ".astack-state"
    astack_state.mkdir(parents=True, exist_ok=True)
    dispatch_state = ws / ".astack-dispatches"
    dispatch_state.mkdir(parents=True, exist_ok=True)
    xdg_cache = ws / ".xdg-cache"
    xdg_cache.mkdir(parents=True, exist_ok=True)
    return {
        "ASTACK_HOME": str(astack_home),
        "ASTACK_STATE_DIR": str(astack_state),
        "ASTACK_DISPATCH_STATE_DIR": str(dispatch_state),
        "XDG_CACHE_HOME": str(xdg_cache),
    }


def run_case(
    case_dir: Path,
    harness: str,
    *,
    binary: str,
    model: str = "",
    effort: str = "",
    pool_override: list[dict[str, Any]] | None = None,
    worker_override: dict[str, Any] | None = None,
    judge_harness: str = "auto",
    timeout: float = 600.0,
    dry_run: bool = False,
    without_plugin: bool = False,
) -> dict[str, Any]:
    meta = parse_case_meta(case_dir)
    case_meta_fields = {
        "tier": meta.get("tier", ""),
        "kind": meta.get("kind", ""),
        "skills": list(meta.get("skills", [])),
    }
    pfields, prompt_body = split_front_matter((case_dir / "prompt.md").read_text(encoding="utf-8"))
    if "timeout_seconds" in pfields:
        try:
            timeout = max(timeout, float(_unquote(pfields["timeout_seconds"])))
        except ValueError:
            pass

    # Determine settings override if applicable
    settings_override: dict[str, Any] | None = None
    if pool_override is not None or worker_override is not None:
        settings_override = {
            "roles": {"worker": worker_override or (DEFAULT_HARNESS_SETTINGS.get(harness, {}).get("roles", {}).get("worker") or {"provider": "anthropic", "model": "haiku", "effort": "medium"})},
            "reviewer_pool": pool_override if pool_override is not None else (DEFAULT_HARNESS_SETTINGS.get(harness, {}).get("reviewer_pool") or []),
        }
    elif harness != "claude" and case_dir.name in ("vectored-review-concurrency", "vectored-review-small-change"):
        settings_override = _default_settings_for_harness(harness)

    with tempfile.TemporaryDirectory(prefix=f"astack-eval-{case_dir.name}-") as scratch:
        ws = Path(scratch)
        # Copy auxiliary fixture directories (e.g. program/RULES.md)
        for child in case_dir.iterdir():
            if child.is_dir() and child.name not in ("graders", "__pycache__"):
                shutil.copytree(child, ws / child.name, dirs_exist_ok=True)
        # Run scaffold_script if present
        scaffold_name = meta.get("scaffold_script")
        if scaffold_name and (case_dir / scaffold_name).is_file():
            sc_env = dict(os.environ)
            if settings_override is not None:
                sc_env["ASTACK_EVAL_SETTINGS_JSON"] = json.dumps(settings_override, indent=2)
            proc_sc = subprocess.run(["bash", str(case_dir / scaffold_name)], cwd=ws, env=sc_env, capture_output=True, text=True)
            if proc_sc.returncode != 0:
                return {
                    "case": case_dir.name,
                    "harness": harness,
                    **case_meta_fields,
                    "score": 0.0,
                    "error": f"{scaffold_name} failed: {proc_sc.stderr}",
                }

        active_settings: dict[str, Any] | None = None
        settings_file = ws / "program" / "settings.json"
        if settings_file.is_file():
            try:
                active_settings = json.loads(settings_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                active_settings = None

        # Isolate per-trial state directories for BOTH with and without arms
        isolation_env = _build_trial_isolation_env(ws)

        if without_plugin:
            env_over, extra_args = {}, []
            if harness == "codex":
                # Isolate CODEX_HOME on baseline arm so host-installed skills/agents don't contaminate ablation
                bare_codex = ws / ".codex_home_without"
                bare_codex.mkdir(parents=True, exist_ok=True)
                src_codex = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex")).expanduser()
                for fname in ("auth.json", "config.toml"):
                    src_f = src_codex / fname
                    try:
                        if src_f.is_file():
                            shutil.copy2(src_f, bare_codex / fname)
                    except OSError:
                        pass
                env_over["CODEX_HOME"] = str(bare_codex)
            elif harness == "agy":
                extra_args.append("--disable-slash-commands")
            # Strip skill-invocation prefix so baseline arm runs the exact same user task without astack
            clean_prompt = re.sub(r"`?/astack:go`?\s*", "", prompt_body.strip())
            prompt_text = adapt_prompt(clean_prompt, harness, active_settings)
        else:
            env_over, extra_args = mount_harness_into_workspace(harness, ws, active_settings)
            prompt_text = adapt_prompt(prompt_body, harness, active_settings)
        argv, stdin_text = build_eval_command(
            harness, binary, prompt_text, ws, extra_args=extra_args, model=model, effort=effort
        )

        if dry_run:
            return {
                "case": case_dir.name,
                "harness": harness,
                **case_meta_fields,
                "dry_run": True,
                "argv": argv,
                "settings": active_settings,
                "prompt": prompt_text,
            }

        receipt_dir = ws / "program" / "dispatch-receipts"
        receipt_dir.mkdir(parents=True, exist_ok=True)
        run_env = {
            **os.environ,
            **env_over,
            **isolation_env,
            "ASTACK_DISPATCH_RECEIPT_DIR": str(receipt_dir),
        }
        started = time.monotonic()
        try:
            proc = subprocess.run(argv, input=stdin_text, cwd=ws, env=run_env, capture_output=True, text=True, timeout=timeout)
            timed_out = False
            exit_code = proc.returncode
            stdout, stderr = proc.stdout, proc.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            exit_code = 124
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        duration_s = round(time.monotonic() - started, 2)

        final_text, events = parse_harness_events(harness, stdout, workspace=ws, settings=active_settings)
        usage = _extract_token_usage(stdout)
        errors = [e["message"] for e in events if e.get("kind") == "error"]
        launch_failed = (
            timed_out
            or exit_code != 0
            or (not final_text.strip() and len(events) == 0)
            or (bool(errors) and not final_text.strip())
        )

        # Runtime gate: never award partial credit to a run that failed to launch, timed out, or crashed
        results: list[dict[str, Any]] = []
        if launch_failed:
            fail_reason = (
                f"timed out after {timeout}s"
                if timed_out
                else f"exit code {exit_code}: {(stderr.strip() or '; '.join(errors) or 'no output')[:180]}"
            )
            results.append({"name": "harness-run", "type": "runtime", "passed": False, "detail": fail_reason})
            return {
                "case": case_dir.name,
                "harness": harness,
                **case_meta_fields,
                "exit_code": exit_code,
                "timed_out": timed_out,
                "launch_failed": True,
                "duration_s": duration_s,
                "score": 0.0,
                "outcome_score": 0.0,
                "process_score": 0.0,
                "usage": usage,
                "events_count": len(events),
                "errors": errors or ([stderr.strip()[:240]] if stderr.strip() else []),
                "graders": results,
                "final_text_preview": final_text[:600],
                "stderr_preview": stderr[:400],
            }

        results.append({"name": "harness-run", "type": "runtime", "passed": True, "detail": f"exit 0 ({len(events)} event(s))"})

        # Executable workspace outcome verifier (`verify.py` in case dir, if present) runs BEFORE LLM judges
        # so deterministic checks inspect the exact post-agent workspace before any judge invocation.
        verify_script = case_dir / "verify.py"
        if verify_script.is_file():
            events_file = ws / ".astack-eval-events.json"
            events_file.write_text(json.dumps(events, indent=2), encoding="utf-8")
            v_env = {
                **os.environ,
                **isolation_env,
                "ASTACK_EVAL_FINAL_TEXT": final_text,
                "ASTACK_EVAL_HARNESS": harness,
                "ASTACK_EVAL_EVENTS_JSON": str(events_file),
            }
            try:
                v_proc = subprocess.run(
                    [sys.executable, "-B", str(verify_script), str(ws)],
                    cwd=ws,
                    env=v_env,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
            except subprocess.TimeoutExpired:
                v_ok = False
                v_detail = "verify.py timed out"
            else:
                v_ok = v_proc.returncode == 0
                v_detail = (v_proc.stdout.strip() or v_proc.stderr.strip() or f"exit {v_proc.returncode}")[:200]
            results.append({"name": "workspace-verify", "type": "command", "passed": v_ok, "detail": v_detail})

        # Grade all declarative graders
        resolved_judge = harness if judge_harness == "auto" else judge_harness
        for grader_path in sorted((case_dir / "graders").glob("*.md")):
            gfields, gbody = split_front_matter(grader_path.read_text(encoding="utf-8"))
            gtype = _unquote(gfields.get("type", ""))
            if gtype == "regex":
                ok, detail = evaluate_regex_grader(gfields, final_text, active_settings)
                results.append({"name": grader_path.stem, "type": gtype, "passed": ok, "detail": detail})
            elif gtype == "tool_used":
                ok, detail = evaluate_tool_grader(gfields, events, active_settings)
                results.append({"name": grader_path.stem, "type": gtype, "passed": ok, "detail": detail})
            elif gtype == "llm":
                if resolved_judge == "none":
                    results.append({"name": grader_path.stem, "type": gtype, "passed": None, "detail": "skipped (--judge-harness none)"})
                else:
                    ok, detail = run_llm_judge(resolved_judge, gbody, final_text, active_settings, workspace=ws)
                    results.append({"name": grader_path.stem, "type": gtype, "passed": ok, "detail": detail})

        score, outcome_score, process_score = _summarize_scores(results)
        return {
            "case": case_dir.name,
            "harness": harness,
            **case_meta_fields,
            "exit_code": exit_code,
            "timed_out": timed_out,
            "launch_failed": False,
            "duration_s": duration_s,
            "score": score,
            "outcome_score": outcome_score,
            "process_score": process_score,
            "usage": usage,
            "events_count": len(events),
            "errors": errors,
            "graders": results,
            "final_text_preview": final_text[:600],
            "stderr_preview": stderr[:400] if exit_code != 0 else "",
        }


def parse_proven_bugs_json(text: str) -> dict[str, Any] | None:
    """Extract structured `PROVEN_BUGS_JSON: {...}` payload emitted by `scripts/repro_verify.py`."""
    for line in reversed(text.splitlines()):
        if line.startswith("PROVEN_BUGS_JSON:"):
            raw = line.split(":", 1)[1].strip()
            try:
                data = json.loads(raw)
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                return None
    return None


def default_provider_for_harness(harness: str) -> str:
    return {
        "claude": "anthropic",
        "codex": "openai",
        "agy": "google",
        "cursor": "cursor",
        "devin": "devin",
        "pi": "pi",
    }.get(harness, harness)


def default_calibration_path(project: str | None = None) -> Path:
    """Default per-project priors/calibration path (`~/.astack/<project>/priors/priors.json`, or legacy global fallback)."""
    if project:
        astack_home = Path(os.environ.get("ASTACK_HOME") or (Path.home() / ".astack")).expanduser()
        return astack_home / project.strip().lower() / "priors" / "priors.json"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg).expanduser() if xdg else (Path.home() / ".config")
    return base / "astack" / "calibration.json"


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def calibrate_model(
    harness: str,
    *,
    binary: str,
    provider: str = "",
    model: str = "",
    effort: str = "",
    detector_version: str = "",
    repo: Path | None = None,
    items_path: Path | None = None,
    runs: int = 1,
    timeout: float = 600.0,
    out_path: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Calibrate a detector on repo-local replayed history (`--repo` + `--items`) through the real review flow.

    - Repo-local path (`repo` + `items_path`): verifies every item with `verify_replay_item` (two-tree
      witness + rerun stability + git-blame attribution), runs the detector blind on each introducing
      change with zero language assumptions, grades catches strictly via `verify_catch` (two trees +
      exit codes), and writes dated `CalibrationTrial` entries per project (`~/.astack/<project>/priors/priors.json`).
    - Bundled fixture fallback (when `--repo`/`--items` are omitted): tagged strictly as
      `source="transferred_prior"` so it enters the Law-2 mixture only as a priced external prior.
    """
    resolved_provider = provider or default_provider_for_harness(harness)
    resolved_model = model or (_detect_codex_default_model() if harness == "codex" else "default")
    model_key = f"{resolved_provider}/{resolved_model}"

    if repo is not None and items_path is not None:
        repo_p = Path(repo).expanduser().resolve()
        items_raw = json.loads(Path(items_path).expanduser().read_text(encoding="utf-8"))
        items = items_raw.get("items") if isinstance(items_raw, dict) else items_raw
        if not isinstance(items, list) or not items:
            raise ValueError("--items must contain a JSON list (or {\"items\": [...]}) of replay items")
        target_file = out_path or default_calibration_path(project=repo_p.name)
        if dry_run:
            return {
                "dry_run": True,
                "mode": "repo_replayed_history",
                "model_key": model_key,
                "harness": harness,
                "repo": str(repo_p),
                "items_count": len(items),
                "out_path": str(target_file),
            }
        raise ValueError(
            "Repo-local replay calibration is agent-directed (see skills/review/SKILL.md): "
            "replay real past bugs through the review flow and grade catches with two trees + exit codes."
        )

    case_dir = EVALS_DIR / "vectored-review-planted-bugs"
    cal_prompt = (
        "Review branch `lane/order-checkout` against `main` in `repo/` (diff saved at `program/change.diff`). "
        "Work strictly as a single read-only reviewer: NEVER modify `repo/`. "
        "For every blocking bug you prove, save a standalone failing reproduction script in `program/repros/` "
        "that exits non-zero on the buggy `repo/` and exits 0 once the bug is fixed. "
        "Keep reproductions focused on genuine blocking bugs (do not fabricate false positives)."
    )

    if dry_run:
        with tempfile.TemporaryDirectory(prefix="astack-cal-dry-") as scratch:
            ws = Path(scratch)
            env_over, extra_args = mount_harness_into_workspace(harness, ws, None)
            argv, _ = build_eval_command(
                harness, binary, cal_prompt, ws, extra_args=extra_args, model=model, effort=effort
            )
            return {
                "dry_run": True,
                "model_key": model_key,
                "harness": harness,
                "runs": max(1, runs),
                "argv": argv,
                "out_path": str(out_path or default_calibration_path()),
            }

    total_detected = 0
    total_planted = 0
    per_bug_counts: dict[str, dict[str, int]] = {}
    per_run: list[dict[str, Any]] = []
    verify_script = case_dir / "verify.py"

    for run_idx in range(1, max(1, runs) + 1):
        with tempfile.TemporaryDirectory(prefix=f"astack-cal-{run_idx}-") as scratch:
            ws = Path(scratch)
            proc_sc = subprocess.run(
                ["bash", str(case_dir / "setup.sh")], cwd=ws, capture_output=True, text=True
            )
            if proc_sc.returncode != 0:
                raise RuntimeError(f"setup.sh failed: {proc_sc.stderr}")
            isolation_env = _build_trial_isolation_env(ws)
            env_over, extra_args = mount_harness_into_workspace(harness, ws, None)
            argv, stdin_text = build_eval_command(
                harness, binary, cal_prompt, ws, extra_args=extra_args, model=model, effort=effort
            )
            run_env = {**os.environ, **env_over, **isolation_env}
            started = time.monotonic()
            try:
                proc = subprocess.run(
                    argv, input=stdin_text, cwd=ws, env=run_env, capture_output=True, text=True, timeout=timeout
                )
                exit_code = proc.returncode
                timed_out = False
            except subprocess.TimeoutExpired:
                exit_code = 124
                timed_out = True
            duration_s = round(time.monotonic() - started, 2)

            v_env = {**os.environ, **isolation_env}
            try:
                v_proc = subprocess.run(
                    [sys.executable, "-B", str(verify_script), str(ws)],
                    cwd=ws,
                    env=v_env,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                v_stdout = v_proc.stdout
            except subprocess.TimeoutExpired:
                v_stdout = ""
            parsed = parse_proven_bugs_json(v_stdout) or {
                "detected": [],
                "missed": [],
                "detected_count": 0,
                "planted_count": 5,
            }
            det_list = list(parsed.get("detected", []))
            miss_list = list(parsed.get("missed", []))
            det = int(parsed.get("detected_count", len(det_list)))
            plt = int(parsed.get("planted_count", len(det_list) + len(miss_list) or 5))
            for bug_id in det_list:
                rec = per_bug_counts.setdefault(bug_id, {"detected": 0, "trials": 0})
                rec["detected"] += 1
                rec["trials"] += 1
            for bug_id in miss_list:
                rec = per_bug_counts.setdefault(bug_id, {"detected": 0, "trials": 0})
                rec["trials"] += 1
            total_detected += det
            total_planted += plt
            per_run.append(
                {
                    "run": run_idx,
                    "exit_code": exit_code,
                    "timed_out": timed_out,
                    "duration_s": duration_s,
                    "detected": det_list,
                    "missed": miss_list,
                    "detected_count": det,
                    "planted_count": plt,
                }
            )

    unique_bugs = len(per_bug_counts)
    expected_missed = round(sum(1.0 - (rec["detected"] / rec["trials"]) for rec in per_bug_counts.values() if rec["trials"] > 0), 4)
    observed_rate = round(total_detected / total_planted, 4) if total_planted else 0.0
    # Compute finite-sample uncertainty strictly over unique_bugs (NEVER inflated by repeated runs, ZERO arbitrary 0.05!)
    jeffreys_miss = round((expected_missed + 0.5) / (unique_bugs + 1.0), 4) if unique_bugs else 1.0
    mvue_moments: dict[str, float] = {}
    bug_trials = [(rec["detected"], rec["trials"]) for rec in per_bug_counts.values() if rec["trials"] > 0]
    if bug_trials:
        import math as _math
        import statistics as _stats

        max_t = max(t for _, t in bug_trials)
        for k in range(1, max_t + 1):
            vals = [
                0.0 if (t - c) < k else float(_math.comb(t - c, k)) / float(_math.comb(t, k))
                for c, t in bug_trials
                if t >= k
            ]
            if vals:
                mvue_moments[str(k)] = round(_stats.fmean(vals), 6)
    entry = {
        "detected": total_detected,
        "planted": total_planted,
        "unique_bugs": unique_bugs,
        "expected_missed": expected_missed,
        "observed_rate": observed_rate,
        "jeffreys_miss_prob": jeffreys_miss,
        "mvue_moments": mvue_moments,
        "per_bug": {k: per_bug_counts[k] for k in sorted(per_bug_counts)},
        "runs": max(1, runs),
        "harness": harness,
        "source": "transferred_prior",
        "fixture": "vectored-review-planted-bugs",
    }

    target_file = out_path or default_calibration_path()
    existing: dict[str, Any] = {"schema_version": "1.1", "models": {}}
    if target_file.is_file():
        try:
            loaded = json.loads(target_file.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and isinstance(loaded.get("models"), dict):
                existing = loaded
                existing["schema_version"] = "1.1"
        except (OSError, json.JSONDecodeError):
            pass
    existing["models"][model_key] = entry
    _atomic_write_json(target_file, existing)

    return {
        "model_key": model_key,
        "entry": entry,
        "runs": per_run,
        "out_path": str(target_file),
    }


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Compute the Wilson score confidence interval for a binomial proportion."""
    if total <= 0:
        return (0.0, 0.0)
    k = max(0, min(successes, total))
    p = k / total
    z2 = z * z
    denom = 1.0 + z2 / total
    center = (p + z2 / (2.0 * total)) / denom
    margin = (z * math.sqrt((p * (1.0 - p) + z2 / (4.0 * total)) / total)) / denom
    return (max(0.0, round(center - margin, 4)), min(1.0, round(center + margin, 4)))


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 2)
    idx = (len(ordered) - 1) * (pct / 100.0)
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    val = ordered[lo] + (ordered[hi] - ordered[lo]) * (idx - lo)
    return round(val, 2)


def _trial_outcome(report: dict[str, Any]) -> float:
    if report.get("outcome_score") is not None:
        return float(report["outcome_score"])
    return float(report.get("score", 0.0))


def _compute_arm_stats(
    trials: list[dict[str, Any]],
    *,
    case_arm_list: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    n = len(trials)
    if n == 0:
        return {
            "trials": 0,
            "outcome_mean": 0.0,
            "pass_rate": 0.0,
            "pass_at_k": 0.0,
            "pass_pow_k": 0.0,
            "wilson_ci_95": [0.0, 0.0],
            "p50_duration_s": 0.0,
            "p95_duration_s": 0.0,
            "total_tokens": 0,
            "tokens_per_pass": None,
        }
    outcomes = [_trial_outcome(t) for t in trials]
    passes = sum(1 for o in outcomes if o == 1.0)
    durations = [float(t.get("duration_s", 0.0)) for t in trials]
    total_tokens = sum(int((t.get("usage") or {}).get("total_tokens", 0)) for t in trials)
    if case_arm_list is not None:
        valid_cases = [c for c in case_arm_list if c["trials"] > 0]
        pass_at_k = round(sum(c["pass_at_k"] for c in valid_cases) / len(valid_cases), 4) if valid_cases else 0.0
        pass_pow_k = round(sum(c["pass_pow_k"] for c in valid_cases) / len(valid_cases), 4) if valid_cases else 0.0
    else:
        pass_at_k = 1.0 if passes >= 1 else 0.0
        pass_pow_k = 1.0 if passes == n else 0.0
    lo, hi = wilson_interval(passes, n)
    return {
        "trials": n,
        "outcome_mean": round(sum(outcomes) / n, 4),
        "pass_rate": round(passes / n, 4),
        "pass_at_k": pass_at_k,
        "pass_pow_k": pass_pow_k,
        "wilson_ci_95": [lo, hi],
        "p50_duration_s": _percentile(durations, 50.0),
        "p95_duration_s": _percentile(durations, 95.0),
        "total_tokens": total_tokens,
        "tokens_per_pass": round(total_tokens / passes, 2) if passes > 0 else None,
    }


def summarize_reports(reports: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute per-case and overall `with` vs `without` statistics across eval trial reports."""
    live = [r for r in reports if not r.get("dry_run")]
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
    meta_by_case: dict[str, dict[str, Any]] = {}

    for r in live:
        cname = str(r.get("case", "unknown"))
        arm = str(r.get("arm") or "with")
        grouped.setdefault(cname, {"with": [], "without": []})
        if arm not in grouped[cname]:
            grouped[cname][arm] = []
        grouped[cname][arm].append(r)
        if cname not in meta_by_case:
            meta_by_case[cname] = {
                "tier": r.get("tier", ""),
                "kind": r.get("kind", ""),
                "skills": list(r.get("skills") or []),
            }

    cases_summary: dict[str, dict[str, Any]] = {}
    all_with: list[dict[str, Any]] = []
    all_without: list[dict[str, Any]] = []
    per_case_with_stats: list[dict[str, Any]] = []
    per_case_without_stats: list[dict[str, Any]] = []

    for cname in sorted(grouped):
        w_trials = grouped[cname].get("with", [])
        wo_trials = grouped[cname].get("without", [])
        all_with.extend(w_trials)
        all_without.extend(wo_trials)

        w_stats = _compute_arm_stats(w_trials)
        per_case_with_stats.append(w_stats)
        wo_stats = _compute_arm_stats(wo_trials) if wo_trials else None
        if wo_stats is not None:
            per_case_without_stats.append(wo_stats)
        delta = (
            round(w_stats["outcome_mean"] - wo_stats["outcome_mean"], 4)
            if (w_stats["trials"] > 0 and wo_stats is not None and wo_stats["trials"] > 0)
            else None
        )
        cases_summary[cname] = {
            **meta_by_case[cname],
            "with": w_stats,
            "without": wo_stats,
            "delta": delta,
        }

    overall_with = _compute_arm_stats(all_with, case_arm_list=per_case_with_stats)
    overall_without = _compute_arm_stats(all_without, case_arm_list=per_case_without_stats) if all_without else None
    overall_delta = (
        round(overall_with["outcome_mean"] - overall_without["outcome_mean"], 4)
        if (overall_with["trials"] > 0 and overall_without is not None and overall_without["trials"] > 0)
        else None
    )
    return {
        "cases": cases_summary,
        "overall": {
            "with": overall_with,
            "without": overall_without,
            "delta": overall_delta,
        },
    }


def _fmt_pct(val: float) -> str:
    return f"{val * 100:.1f}%"


def _fmt_delta(delta: float | None) -> str:
    if delta is None:
        return "-"
    sign = "+" if delta > 0 else ""
    return f"{sign}{delta * 100:.1f}pp"


def _fmt_tok_per_pass(val: float | None) -> str:
    if val is None:
        return "-"
    return f"{val:,.0f}"


def render_markdown_scorecard(summary: dict[str, Any]) -> str:
    """Render a GitHub-flavored Markdown scorecard from `summarize_reports()` output."""
    overall = summary.get("overall") or {}
    ow = overall.get("with") or {}
    owo = overall.get("without")
    odelta = overall.get("delta")

    lines = [
        "# astack Eval Scorecard",
        "",
        "| Case | Tier | Kind | With (Pass / 95% CI) | pass@k | pass^k | Without | Delta | p50 / p95 (s) | Tok/Pass |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    cases = summary.get("cases") or {}
    for cname in sorted(cases):
        entry = cases[cname]
        w = entry["with"]
        wo = entry.get("without")
        ci = w["wilson_ci_95"]
        with_cell = f"{_fmt_pct(w['pass_rate'])} ({w['outcome_mean']:.2f}) [{ci[0]:.2f}, {ci[1]:.2f}]"
        wo_cell = f"{_fmt_pct(wo['pass_rate'])} ({wo['outcome_mean']:.2f})" if wo else "-"
        dur_cell = f"{w['p50_duration_s']:.1f} / {w['p95_duration_s']:.1f}"
        lines.append(
            f"| `{cname}` | {entry.get('tier') or '-'} | {entry.get('kind') or '-'} | {with_cell} | "
            f"{_fmt_pct(w['pass_at_k'])} | {_fmt_pct(w['pass_pow_k'])} | {wo_cell} | "
            f"{_fmt_delta(entry.get('delta'))} | {dur_cell} | {_fmt_tok_per_pass(w.get('tokens_per_pass'))} |"
        )

    if ow:
        oci = ow.get("wilson_ci_95") or [0.0, 0.0]
        ow_cell = f"{_fmt_pct(ow['pass_rate'])} ({ow['outcome_mean']:.2f}) [{oci[0]:.2f}, {oci[1]:.2f}]"
        owo_cell = f"{_fmt_pct(owo['pass_rate'])} ({owo['outcome_mean']:.2f})" if owo else "-"
        odur_cell = f"{ow['p50_duration_s']:.1f} / {ow['p95_duration_s']:.1f}"
        lines.append(
            f"| **Overall** | - | - | **{ow_cell}** | **{_fmt_pct(ow['pass_at_k'])}** | "
            f"**{_fmt_pct(ow['pass_pow_k'])}** | {owo_cell} | **{_fmt_delta(odelta)}** | "
            f"{odur_cell} | {_fmt_tok_per_pass(ow.get('tokens_per_pass'))} |"
        )
    lines.append("")
    return "\n".join(lines)


def verify_offline_oracles(
    oracles_dir: Path = ORACLES_DIR,
    *,
    allowed_cases: set[str] | None = None,
) -> tuple[bool, list[dict[str, Any]]]:
    """Run RED -> GREEN verification across separated oracle modules in `oracles_dir`."""
    if not oracles_dir.is_dir():
        return False, []
    oracle_paths = sorted(
        p for p in oracles_dir.glob("*.py")
        if p.is_file() and not p.name.startswith("_")
    )
    if allowed_cases is not None:
        oracle_paths = [p for p in oracle_paths if p.stem in allowed_cases]

    results: list[dict[str, Any]] = []
    all_ok = bool(oracle_paths)
    for oracle_path in oracle_paths:
        case_dir = EVALS_DIR / oracle_path.stem
        ok, detail = _eval_kit.run_oracle_check(case_dir, oracle_path)
        results.append({"case": oracle_path.stem, "oracle": str(oracle_path), "passed": ok, "detail": detail})
        if not ok:
            all_ok = False
    return all_ok, results


def _print_case_result(res: dict[str, Any], runs: int) -> None:
    arm = res.get("arm", "with")
    run_idx = res.get("run", 1)
    if res.get("dry_run"):
        print(f"[DRY-RUN] {res['case']} ({res['harness']}/{arm}): {' '.join(res['argv'][:8])} ...")
        return
    mark = "✓" if res.get("score", 0) == 1.0 else "✗"
    out_part = f"  outcome {res['outcome_score']:.2f}" if res.get("outcome_score") is not None else ""
    tok_total = int((res.get("usage") or {}).get("total_tokens", 0))
    tok_part = f", {tok_total} tok" if tok_total > 0 else ""
    print(
        f"{mark} {res['case']} ({res['harness']}/{arm} {run_idx}/{runs})  "
        f"score {res.get('score', 0):.2f}{out_part}  ({res.get('duration_s', 0)}s{tok_part})"
    )
    for g in res.get("graders", []):
        gm = "✓" if g["passed"] is True else ("-" if g["passed"] is None else "✗")
        print(f"    {gm} {g['name']} ({g['type']}): {g['detail']}")
    for err in res.get("errors", []):
        print(f"    ! error: {err}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run astack evals across Claude, Codex, Antigravity, Cursor CLI, Devin, or Pi.")
    parser.add_argument("--harness", default=None, choices=SUPPORTED_HARNESSES, help="target host harness")
    parser.add_argument("--case", default="*", help="case name glob or comma-separated globs (default: *)")
    parser.add_argument("--tier", default=None, choices=_eval_kit.VALID_TIERS, help="cumulative tier filter (smoke, core, deep)")
    parser.add_argument("--kind", default=None, choices=_eval_kit.VALID_KINDS, help="exact case kind filter (atomic, capstone, negative)")
    parser.add_argument("--skill", action="append", default=[], help="filter by skill name (repeatable or comma-separated)")
    parser.add_argument("--select-from-diff", metavar="BASE", default=None, help="auto-select eval cases affected by git diff against BASE")
    parser.add_argument("--list-selected", action="store_true", help="print selected case names and exit 0")
    parser.add_argument("--verify-offline", action="store_true", help="run RED -> GREEN verification across separated eval oracles")
    parser.add_argument("--parallel", type=int, default=1, help="number of parallel worker threads (default: 1)")
    parser.add_argument("--report-out", default="", help="write JSON report and summary to PATH")
    parser.add_argument("--markdown-out", default="", help="write GitHub Markdown scorecard to PATH")
    parser.add_argument("--provider", default="", help="provider name for --calibrate (default: inferred from harness)")
    parser.add_argument("--model", default="", help="override host harness model")
    parser.add_argument("--effort", default="", help="override host harness effort")
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="calibrate detector on target repo replay items (--repo + --items) or bundled transferred-prior fixture",
    )
    parser.add_argument("--repo", default="", help="target repository path for repo-local --calibrate")
    parser.add_argument("--items", default="", help="JSON file of replay items (introducing_commit, fix_commit, witness_cmd) for --calibrate")
    parser.add_argument("--detector-version", default="", help="optional detector version tag recorded on calibration trials")
    parser.add_argument(
        "--calibration-out",
        default="",
        help="output path for --calibrate (default: ~/.astack/<project>/priors/priors.json when --repo is set)",
    )
    parser.add_argument("--reviewer-pool", help="JSON list (or path to JSON file) overriding program/settings.json reviewer_pool")
    parser.add_argument("--worker-model", help="JSON object overriding roles.worker in program/settings.json")
    parser.add_argument(
        "--judge-harness",
        default="auto",
        choices=("auto", "none", *SUPPORTED_HARNESSES),
        help="harness used for llm graders (default: auto = same as --harness; 'none' skips llm graders)",
    )
    parser.add_argument(
        "--ablation",
        default="none",
        choices=("none", "with-without"),
        help="run a no-plugin baseline arm alongside the with-plugin arm to measure real delta",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="number of trials per case/arm (default: 1; use 3+ for variance-checked ablation)",
    )
    parser.add_argument("--timeout", type=float, default=600.0, help="per-case timeout in seconds")
    parser.add_argument("--dry-run", action="store_true", help="print resolved commands without executing")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    has_explicit_filter = (
        args.case != "*"
        or args.tier is not None
        or args.kind is not None
        or bool(args.skill)
        or args.select_from_diff is not None
    )

    if args.select_from_diff is not None:
        cases = select_cases_from_diff(args.select_from_diff)
        if args.case != "*" or args.tier is not None or args.kind is not None or args.skill:
            allowed = set(
                discover_cases(
                    args.case,
                    tier=args.tier,
                    kind=args.kind,
                    skills_filter=args.skill,
                )
            )
            cases = [c for c in cases if c in allowed]
    else:
        cases = discover_cases(
            args.case,
            tier=args.tier,
            kind=args.kind,
            skills_filter=args.skill,
        )

    if args.verify_offline:
        allowed_names = {c.name for c in cases} if has_explicit_filter else None
        all_ok, oracle_results = verify_offline_oracles(ORACLES_DIR, allowed_cases=allowed_names)
        if not oracle_results:
            print("error: no separated eval oracles matched", file=sys.stderr)
            return 1
        if args.as_json:
            print(json.dumps(oracle_results, indent=2))
        else:
            for item in oracle_results:
                tag = "PASS" if item["passed"] else "FAIL"
                print(f"[{tag}] {item['detail']}")
        return 0 if all_ok else 1

    if args.list_selected:
        if not cases and (args.select_from_diff is None or not [p.strip() for p in args.case.split(",") if p.strip()]):
            print(f"error: no eval cases matched {args.case!r}", file=sys.stderr)
            return 2
        if args.as_json:
            print(json.dumps([c.name for c in cases], indent=2))
        else:
            for c in cases:
                print(c.name)
        return 0

    if not args.harness:
        print("error: --harness is required unless --list-selected or --verify-offline is specified", file=sys.stderr)
        return 2

    if not args.calibrate and not cases:
        print(f"error: no eval cases matched {args.case!r}", file=sys.stderr)
        return 2

    binary = find_harness_binary(args.harness)
    if not binary and not args.dry_run:
        print(f"error: harness {args.harness!r} CLI not found ({', '.join(HARNESS_BINARIES[args.harness])})", file=sys.stderr)
        return 2
    binary = binary or HARNESS_BINARIES[args.harness][0]

    if args.calibrate:
        repo_arg = Path(args.repo).expanduser() if args.repo else None
        items_arg = Path(args.items).expanduser() if args.items else None
        cal_out = (
            Path(args.calibration_out).expanduser()
            if args.calibration_out
            else default_calibration_path(project=repo_arg.name if repo_arg else None)
        )
        cal = calibrate_model(
            args.harness,
            binary=binary,
            provider=args.provider,
            model=args.model,
            effort=args.effort,
            detector_version=args.detector_version,
            repo=repo_arg,
            items_path=items_arg,
            runs=args.runs,
            timeout=args.timeout,
            out_path=cal_out,
            dry_run=args.dry_run,
        )
        if args.as_json:
            print(json.dumps(cal, indent=2))
        elif cal.get("dry_run"):
            print(f"[DRY-RUN CALIBRATE] {cal['model_key']} ({cal['harness']}) -> {cal['out_path']}")
        elif cal.get("mode") == "repo_replayed_history":
            acc = sum(1 for r in cal["results"] if r.get("accepted"))
            cgt = sum(1 for r in cal["results"] if r.get("caught"))
            print(f"Calibrated {cal['model_key']} on {cal['repo']}: caught {cgt}/{acc} accepted replay item(s) -> {cal['out_path']}")
        else:
            ent = cal["entry"]
            print(
                f"Recorded transferred-prior fixture {cal['model_key']}: detected {ent['detected']}/{ent['planted']} across "
                f"{ent['unique_bugs']} unique bug(s) ({ent['runs']} run(s), posterior miss {ent['jeffreys_miss_prob']*100:.1f}%) -> {cal['out_path']}"
            )
        return 0

    pool_override: list[dict[str, Any]] | None = None
    if args.reviewer_pool:
        p = Path(args.reviewer_pool)
        raw = p.read_text(encoding="utf-8") if p.is_file() else args.reviewer_pool
        pool_override = json.loads(raw)

    worker_override: dict[str, Any] | None = json.loads(args.worker_model) if args.worker_model else None

    arms = ("with", "without") if args.ablation == "with-without" else ("with",)
    tasks: list[tuple[Path, str, int]] = [
        (case, arm, run_idx)
        for case in cases
        for arm in arms
        for run_idx in range(1, max(1, args.runs) + 1)
    ]

    def _exec_task(task: tuple[Path, str, int]) -> dict[str, Any]:
        case, arm, run_idx = task
        res = run_case(
            case,
            args.harness,
            binary=binary,
            model=args.model,
            effort=args.effort,
            pool_override=pool_override,
            worker_override=worker_override,
            judge_harness=args.judge_harness,
            timeout=args.timeout,
            dry_run=args.dry_run,
            without_plugin=(arm == "without"),
        )
        res["arm"] = arm
        res["run"] = run_idx
        return res

    reports: list[dict[str, Any]] = []
    max_workers = max(1, int(args.parallel))
    if max_workers == 1 or len(tasks) <= 1:
        for task in tasks:
            res = _exec_task(task)
            reports.append(res)
            if not args.as_json:
                _print_case_result(res, args.runs)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_exec_task, task) for task in tasks]
            for fut in futures:
                res = fut.result()
                reports.append(res)
                if not args.as_json:
                    _print_case_result(res, args.runs)

    summary = summarize_reports(reports) if not args.dry_run else {}
    if args.report_out:
        out_p = Path(args.report_out).expanduser()
        payload = {"reports": reports, "summary": summary} if not args.dry_run else {"reports": reports}
        _atomic_write_json(out_p, payload)
    if args.markdown_out and not args.dry_run:
        md_p = Path(args.markdown_out).expanduser()
        md_p.parent.mkdir(parents=True, exist_ok=True)
        md_p.write_text(render_markdown_scorecard(summary), encoding="utf-8")

    if args.as_json:
        print(json.dumps(reports, indent=2))
    elif not args.dry_run and args.ablation == "with-without":
        for case in cases:
            w_vals = [r["outcome_score"] for r in reports if r["case"] == case.name and r.get("arm") == "with" and r.get("outcome_score") is not None]
            wo_vals = [r["outcome_score"] for r in reports if r["case"] == case.name and r.get("arm") == "without" and r.get("outcome_score") is not None]
            if w_vals and wo_vals:
                w_avg = round(sum(w_vals) / len(w_vals), 2)
                wo_avg = round(sum(wo_vals) / len(wo_vals), 2)
                delta = round(w_avg - wo_avg, 2)
                sign = "+" if delta > 0 else ""
                print(
                    f"ablation outcome-only ({case.name}): with={w_avg:.2f} vs without={wo_avg:.2f} "
                    f"(delta={sign}{delta:.2f}; process graders excluded)"
                )
        if args.runs < 3:
            print(f"note: --runs {args.runs} ran {args.runs} trial(s) per arm; pass --runs 3+ for variance-checked ablation")
    if args.dry_run:
        return 0
    with_reports = [r for r in reports if r.get("arm") == "with"]
    return 0 if all(r.get("score", 0) == 1.0 for r in with_reports) else 1


if __name__ == "__main__":
    sys.exit(main())
