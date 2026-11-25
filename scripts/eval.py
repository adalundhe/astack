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
import fnmatch
import json
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


def discover_cases(pattern: str = "*") -> list[Path]:
    cases = sorted(p for p in EVALS_DIR.iterdir() if p.is_dir() and (p / "case.yaml").is_file())
    return [c for c in cases if fnmatch.fnmatch(c.name, pattern)]


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
            "-p",
            "--respect-workspace-trust",
            "false",
            "--permission-mode",
            "autonomous",
            "--sandbox",
        ]
        if model:
            argv.extend(["--model", model])
        argv.append(prompt_text)
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
                    for m in re.findall(r"([A-Za-z0-9_./~-]+SKILL\.md)", cmd):
                        events.append({"kind": "read", "target": m, "raw_tool": "Read", "raw_input": json.dumps({"file_path": m})})
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
                for m in re.findall(r"([A-Za-z0-9_./~-]+SKILL\.md)", cmd):
                    events.append({"kind": "read", "target": m, "raw_tool": "Read", "raw_input": json.dumps({"file_path": m})})
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
                for m in re.findall(r"([A-Za-z0-9_./~-]+SKILL\.md)", cmd):
                    events.append({"kind": "read", "target": m, "raw_tool": "Read", "raw_input": json.dumps({"file_path": m})})
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

        for ev in events:
            if ev["kind"] != "spawn":
                continue
            role = ev.get("role", "")
            mod = ev.get("model", "")
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


def run_llm_judge(
    judge_harness: str,
    rubric: str,
    final_text: str,
    settings: dict[str, Any] | None,
    timeout: float = 120.0,
) -> tuple[bool, str]:
    binary = find_harness_binary(judge_harness)
    if not binary:
        return False, f"judge harness {judge_harness!r} not installed"
    ctx = ""
    if settings:
        ctx = f"\nActive settings.json for this run:\n```json\n{json.dumps(settings, indent=2)}\n```\n"
    adapted_rubric = _adapt_model_tokens(rubric, settings)
    prompt = (
        "You are grading an agent's final output against a strict rubric.\n"
        f"{ctx}\nRubric:\n{adapted_rubric.strip()}\n\n"
        f"Agent output:\n---\n{final_text}\n---\n\n"
        "Respond with a single line starting with PASS or FAIL followed by a one-sentence reason."
    )
    with tempfile.TemporaryDirectory(prefix="astack-judge-") as tmp:
        argv, stdin_text = build_eval_command(judge_harness, binary, prompt, Path(tmp))
        try:
            proc = subprocess.run(argv, input=stdin_text, cwd=tmp, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return False, "judge timed out"
    judge_text, _ = parse_harness_events(judge_harness, proc.stdout)
    first = next((ln.strip() for ln in judge_text.splitlines() if ln.strip()), "")
    passed = first.upper().startswith("PASS")
    return passed, f"judge({judge_harness}): {first[:140]}"


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
    yaml_text = (case_dir / "case.yaml").read_text(encoding="utf-8")
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
            if child.is_dir() and child.name != "graders":
                shutil.copytree(child, ws / child.name, dirs_exist_ok=True)
        # Run scaffold_script if present
        if "scaffold_script: setup.sh" in yaml_text and (case_dir / "setup.sh").is_file():
            sc_env = dict(os.environ)
            if settings_override is not None:
                sc_env["ASTACK_EVAL_SETTINGS_JSON"] = json.dumps(settings_override, indent=2)
            proc_sc = subprocess.run(["bash", str(case_dir / "setup.sh")], cwd=ws, env=sc_env, capture_output=True, text=True)
            if proc_sc.returncode != 0:
                return {"case": case_dir.name, "harness": harness, "score": 0.0, "error": f"setup.sh failed: {proc_sc.stderr}"}

        active_settings: dict[str, Any] | None = None
        settings_file = ws / "program" / "settings.json"
        if settings_file.is_file():
            try:
                active_settings = json.loads(settings_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                active_settings = None

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
                "dry_run": True,
                "argv": argv,
                "settings": active_settings,
                "prompt": prompt_text,
            }

        run_env = {**os.environ, **env_over}
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

        # Grade all graders
        results: list[dict[str, Any]] = []
        resolved_judge = harness if judge_harness == "auto" else judge_harness
        for grader_path in sorted((case_dir / "graders").glob("*.md")):
            gfields, gbody = split_front_matter(grader_path.read_text(encoding="utf-8"))
            gtype = _unquote(gfields.get("type", ""))
            if gtype == "regex":
                pat = _adapt_model_tokens(_unquote(gfields.get("pattern", "")), active_settings)
                flags = re.IGNORECASE if "i" in _unquote(gfields.get("flags", "")).lower() else 0
                ok = bool(re.search(pat, final_text, flags))
                detail = f"{'matched' if ok else 'missed'} {pat}"
                results.append({"name": grader_path.stem, "type": gtype, "passed": ok, "detail": detail})
            elif gtype == "tool_used":
                ok, detail = evaluate_tool_grader(gfields, events, active_settings)
                results.append({"name": grader_path.stem, "type": gtype, "passed": ok, "detail": detail})
            elif gtype == "llm":
                if resolved_judge == "none":
                    results.append({"name": grader_path.stem, "type": gtype, "passed": None, "detail": "skipped (--judge-harness none)"})
                else:
                    ok, detail = run_llm_judge(resolved_judge, gbody, final_text, active_settings)
                    results.append({"name": grader_path.stem, "type": gtype, "passed": ok, "detail": detail})

        # Executable workspace outcome verifier (`verify.py` in case dir, if present):
        # checks objective post-run invariants (e.g. repo untouched, real tests pass, real artifacts valid)
        verify_script = case_dir / "verify.py"
        if verify_script.is_file():
            v_env = {**os.environ, "ASTACK_EVAL_FINAL_TEXT": final_text, "ASTACK_EVAL_HARNESS": harness}
            v_proc = subprocess.run(
                [sys.executable, "-B", str(verify_script), str(ws)],
                cwd=ws,
                env=v_env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            v_ok = v_proc.returncode == 0
            v_detail = (v_proc.stdout.strip() or v_proc.stderr.strip() or f"exit {v_proc.returncode}")[:200]
            results.append({"name": "workspace-verify", "type": "command", "passed": v_ok, "detail": v_detail})

        scored = [r for r in results if r["passed"] is not None]
        score = round(sum(1 for r in scored if r["passed"]) / len(scored), 2) if scored else 0.0
        errors = [e["message"] for e in events if e.get("kind") == "error"]
        return {
            "case": case_dir.name,
            "harness": harness,
            "exit_code": exit_code,
            "timed_out": timed_out,
            "duration_s": duration_s,
            "score": score,
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


def default_calibration_path() -> Path:
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
    runs: int = 1,
    timeout: float = 600.0,
    out_path: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Measure one model's real bug-detection rate on `vectored-review-planted-bugs` using `verify.py`.

    Runs the single target model directly (not a multi-model pool) against the 5-bug fixture,
    executes saved reproduction scripts against buggy/fixed/leave-one-bug-in copies via `verify.py`,
    and records the empirical `detected / planted` count for `astack-review-ledger --calibration`.
    """
    case_dir = EVALS_DIR / "vectored-review-planted-bugs"
    resolved_provider = provider or default_provider_for_harness(harness)
    resolved_model = model or (_detect_codex_default_model() if harness == "codex" else "default")
    model_key = f"{resolved_provider}/{resolved_model}"
    cal_prompt = (
        "Review branch `lane/order-checkout` against `main` in `repo/` (diff saved at `program/change.diff`). "
        "Work strictly as a single read-only reviewer: NEVER modify `repo/`. "
        "For every blocking bug you prove, save a standalone failing Python reproduction script in `program/repros/` "
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
            env_over, extra_args = mount_harness_into_workspace(harness, ws, None)
            argv, stdin_text = build_eval_command(
                harness, binary, cal_prompt, ws, extra_args=extra_args, model=model, effort=effort
            )
            run_env = {**os.environ, **env_over}
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

            v_proc = subprocess.run(
                [sys.executable, "-B", str(verify_script), str(ws)],
                cwd=ws,
                capture_output=True,
                text=True,
                timeout=60,
            )
            parsed = parse_proven_bugs_json(v_proc.stdout) or {
                "detected": [],
                "missed": [],
                "detected_count": 0,
                "planted_count": 5,
            }
            det = int(parsed.get("detected_count", 0))
            plt = int(parsed.get("planted_count", 5))
            total_detected += det
            total_planted += plt
            per_run.append(
                {
                    "run": run_idx,
                    "exit_code": exit_code,
                    "timed_out": timed_out,
                    "duration_s": duration_s,
                    "detected": parsed.get("detected", []),
                    "missed": parsed.get("missed", []),
                    "detected_count": det,
                    "planted_count": plt,
                }
            )

    observed_rate = round(total_detected / total_planted, 4) if total_planted else 0.0
    jeffreys_miss = round((total_planted - total_detected + 0.5) / (total_planted + 1.0), 4) if total_planted else 1.0
    entry = {
        "detected": total_detected,
        "planted": total_planted,
        "observed_rate": observed_rate,
        "jeffreys_miss_prob": jeffreys_miss,
        "runs": max(1, runs),
        "harness": harness,
        "source": "vectored-review-planted-bugs",
    }

    target_file = out_path or default_calibration_path()
    existing: dict[str, Any] = {"schema_version": "1.0", "models": {}}
    if target_file.is_file():
        try:
            loaded = json.loads(target_file.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and isinstance(loaded.get("models"), dict):
                existing = loaded
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run astack evals across Claude, Codex, Antigravity, Cursor CLI, Devin, or Pi.")
    parser.add_argument("--harness", required=True, choices=SUPPORTED_HARNESSES, help="target host harness")
    parser.add_argument("--case", default="*", help="case name glob (default: *)")
    parser.add_argument("--provider", default="", help="provider name for --calibrate (default: inferred from harness)")
    parser.add_argument("--model", default="", help="override host harness model")
    parser.add_argument("--effort", default="", help="override host harness effort")
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="measure this single model's empirical catch rate on vectored-review-planted-bugs and save calibration.json",
    )
    parser.add_argument(
        "--calibration-out",
        default="",
        help="output path for --calibrate (default: ~/.config/astack/calibration.json)",
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
    parser.add_argument("--runs", type=int, default=1, help="number of runs per case (default: 1)")
    parser.add_argument("--timeout", type=float, default=600.0, help="per-case timeout in seconds")
    parser.add_argument("--dry-run", action="store_true", help="print resolved commands without executing")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    binary = find_harness_binary(args.harness)
    if not binary and not args.dry_run:
        print(f"error: harness {args.harness!r} CLI not found ({', '.join(HARNESS_BINARIES[args.harness])})", file=sys.stderr)
        return 2
    binary = binary or HARNESS_BINARIES[args.harness][0]

    if args.calibrate:
        cal_out = Path(args.calibration_out).expanduser() if args.calibration_out else default_calibration_path()
        cal = calibrate_model(
            args.harness,
            binary=binary,
            provider=args.provider,
            model=args.model,
            effort=args.effort,
            runs=args.runs,
            timeout=args.timeout,
            out_path=cal_out,
            dry_run=args.dry_run,
        )
        if args.as_json:
            print(json.dumps(cal, indent=2))
        elif cal.get("dry_run"):
            print(f"[DRY-RUN CALIBRATE] {cal['model_key']} ({cal['harness']}, {cal['runs']} run(s)) -> {cal['out_path']}")
        else:
            ent = cal["entry"]
            print(
                f"Calibrated {cal['model_key']}: detected {ent['detected']}/{ent['planted']} planted bugs "
                f"(observed {ent['observed_rate']*100:.1f}%, Jeffreys miss prob {ent['jeffreys_miss_prob']*100:.1f}%) "
                f"-> {cal['out_path']}"
            )
        return 0

    pool_override: list[dict[str, Any]] | None = None
    if args.reviewer_pool:
        p = Path(args.reviewer_pool)
        raw = p.read_text(encoding="utf-8") if p.is_file() else args.reviewer_pool
        pool_override = json.loads(raw)

    worker_override: dict[str, Any] | None = json.loads(args.worker_model) if args.worker_model else None

    cases = discover_cases(args.case)
    if not cases:
        print(f"error: no eval cases matched {args.case!r}", file=sys.stderr)
        return 2

    reports = []
    arms = ("with", "without") if args.ablation == "with-without" else ("with",)
    for case in cases:
        for arm in arms:
            for run_idx in range(1, max(1, args.runs) + 1):
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
                reports.append(res)
                if not args.as_json:
                    if res.get("dry_run"):
                        print(f"[DRY-RUN] {res['case']} ({res['harness']}/{arm}): {' '.join(res['argv'][:8])} ...")
                    else:
                        mark = "✓" if res.get("score", 0) == 1.0 else "✗"
                        print(f"{mark} {res['case']} ({res['harness']}/{arm} {run_idx}/{args.runs})  score {res.get('score', 0):.2f}  ({res.get('duration_s', 0)}s)")
                        for g in res.get("graders", []):
                            gm = "✓" if g["passed"] is True else ("-" if g["passed"] is None else "✗")
                            print(f"    {gm} {g['name']} ({g['type']}): {g['detail']}")
                        for err in res.get("errors", []):
                            print(f"    ! error: {err}")

    if args.as_json:
        print(json.dumps(reports, indent=2))
    if args.dry_run:
        return 0
    with_reports = [r for r in reports if r.get("arm") == "with"]
    return 0 if all(r.get("score", 0) == 1.0 for r in with_reports) else 1


if __name__ == "__main__":
    sys.exit(main())
