"""Behaviour tests for cross-harness dispatch (bin/astack-dispatch) and multi-harness eval runner (scripts/eval.py)."""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "bin"
SCRIPTS = ROOT / "scripts"


def _load_eval_module():
    spec = importlib.util.spec_from_file_location("astack_eval_runner", SCRIPTS / "eval.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _make_stub(directory: Path, name: str, body: str) -> Path:
    path = directory / name
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(0o755)
    return path


class DispatchTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="astack-dispatch-test-"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.stub_bin = self.dir / "bin"
        self.stub_bin.mkdir()
        self.work = self.dir / "work"
        self.work.mkdir()

    def run_dispatch(self, *args, path_dir: Path | None = None, stdin: str | None = None):
        env = {
            **os.environ,
            "PATH": f"{path_dir or self.stub_bin}{os.pathsep}/usr/bin{os.pathsep}/bin",
            "ASTACK_DISPATCH_STRICT_PATH": "1",
        }
        return subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-dispatch"), *args],
            capture_output=True,
            text=True,
            input=stdin,
            env=env,
        )

    def test_harnesses_detects_all_seven_supported_clis(self):
        for cli in ("claude", "codex", "agy", "cursor-agent", "devin", "pi", "gemini"):
            _make_stub(self.stub_bin, cli, "exit 0\n")
        res = self.run_dispatch("harnesses", "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        for name in ("claude", "codex", "agy", "cursor", "devin", "pi", "gemini"):
            self.assertTrue(data[name]["installed"], f"{name} should be detected")
            self.assertTrue(data[name]["path"].startswith(str(self.stub_bin)))

    def test_check_pool_resolves_native_cli_custom_and_unreachable_across_hosts(self):
        for cli in ("codex", "pi", "my-custom-cli"):
            _make_stub(self.stub_bin, cli, "exit 0\n")
        pool = [
            {"provider": "anthropic", "model": "sonnet", "effort": "medium"},
            {"provider": "openai", "model": "gpt-5.4", "effort": "high", "harness": "codex"},
            {"provider": "google", "model": "gemini-2.5-pro", "effort": "medium", "harness": "pi"},
            {"provider": "devin", "model": "default", "harness": "devin"},
            {
                "provider": "openrouter",
                "model": "qwen3-coder",
                "harness": "custom",
                "command": ["my-custom-cli", "--model", "{model}", "--provider", "{provider}"],
            },
        ]
        # Under Claude host: sonnet is native, codex/pi/custom are cli, devin is unreachable -> exit 1
        res = self.run_dispatch("check-pool", "--host", "claude", "--pool-json", json.dumps(pool), "--json")
        self.assertEqual(res.returncode, 1, res.stderr)
        data = json.loads(res.stdout)
        by_model = {e["model"]: e for e in data["entries"]}
        self.assertEqual(by_model["sonnet"]["route"], "native")
        self.assertEqual(by_model["gpt-5.4"]["route"], "cli")
        self.assertEqual(by_model["gpt-5.4"]["resolved_harness"], "codex")
        self.assertEqual(by_model["gemini-2.5-pro"]["route"], "cli")
        self.assertEqual(by_model["gemini-2.5-pro"]["resolved_harness"], "pi")
        self.assertEqual(by_model["qwen3-coder"]["route"], "cli")
        self.assertEqual(by_model["qwen3-coder"]["resolved_harness"], "custom")
        self.assertFalse(by_model["default"]["reachable"])
        self.assertEqual(len(data["could_not_test"]), 1)
        self.assertIn("devin/default", data["could_not_test"][0])

        # Under Codex host with devin installed -> all reachable (exit 0)
        _make_stub(self.stub_bin, "devin", "exit 0\n")
        res_ok = self.run_dispatch("check-pool", "--host", "codex", "--pool-json", json.dumps(pool), "--json")
        self.assertEqual(res_ok.returncode, 0, res_ok.stdout + res_ok.stderr)
        data_ok = json.loads(res_ok.stdout)
        self.assertTrue(data_ok["all_reachable"])
        by_model_ok = {e["model"]: e for e in data_ok["entries"]}
        self.assertEqual(by_model_ok["gpt-5.4"]["route"], "native")
        # sonnet falls back to installed multi-provider pi CLI when claude isn't installed!
        self.assertEqual(by_model_ok["sonnet"]["resolved_harness"], "pi")

    def test_check_pool_rejects_retired_roles_reviewer(self):
        settings = self.dir / "legacy.json"
        settings.write_text(json.dumps({"roles": {"reviewer": {"provider": "anthropic", "model": "sonnet"}}}))
        res = self.run_dispatch("check-pool", "--settings", str(settings))
        self.assertEqual(res.returncode, 2)
        self.assertIn("retired roles.reviewer", res.stderr)

    def test_dry_run_command_shapes_for_all_eight_harness_adapters(self):
        for cli in ("claude", "codex", "agy", "agent", "devin", "pi", "gemini", "opencode"):
            _make_stub(self.stub_bin, cli, "exit 0\n")
        sys_prompt = self.dir / "reviewer.md"
        sys_prompt.write_text("You are an adversarial reviewer.\n")

        cases = [
            ("claude", "anthropic", "claude-opus-4-6", "high", ["--model", "claude-opus-4-6", "--effort", "high", "--append-system-prompt-file"]),
            ("codex", "openai", "gpt-5.4", "high", ["exec", "--model", "gpt-5.4", "--sandbox", "read-only", "--ephemeral"]),
            ("agy", "google", "gemini-2.5-pro", "high", ["-p", "--model", "gemini-2.5-pro", "--effort", "high", "--sandbox"]),
            ("cursor", "cursor", "sonnet-4", "medium", ["-p", "--model", "sonnet-4", "--trust", "--mode", "ask"]),
            ("devin", "devin", "sonnet", "medium", ["-p", "--model", "sonnet", "--respect-workspace-trust", "false", "--sandbox"]),
            ("pi", "openrouter", "deepseek-r1", "high", ["-p", "--provider", "openrouter", "--model", "deepseek-r1", "--thinking", "high", "--tools"]),
            ("gemini", "google", "gemini-2.5-pro", "", ["-m", "gemini-2.5-pro", "-p"]),
        ]
        for harness, prov, mod, eff, must_have in cases:
            args = [
                "run",
                "--harness", harness,
                "--provider", prov,
                "--model", mod,
                "--cwd", str(self.work),
                "--prompt", "Review auth.py",
                "--system-prompt-file", str(sys_prompt),
                "--dry-run",
                "--json",
            ]
            if eff:
                args.extend(["--effort", eff])
            res = self.run_dispatch(*args)
            self.assertEqual(res.returncode, 0, f"{harness}: {res.stderr}")
            preview = json.loads(res.stdout)
            self.assertEqual(preview["harness"], harness)
            for token in must_have:
                self.assertIn(token, preview["argv"], f"{harness} missing {token!r} in {preview['argv']}")

        # Custom CLI template via settings.json
        settings = self.dir / "settings.json"
        settings.write_text(json.dumps({
            "reviewer_pool": [
                {
                    "provider": "openrouter",
                    "model": "qwen3-coder",
                    "effort": "high",
                    "harness": "custom",
                    "command": ["opencode", "run", "--model", "{provider}/{model}", "--dir", "{cwd}"],
                }
            ]
        }))
        res_c = self.run_dispatch(
            "run", "--settings", str(settings), "--provider", "openrouter", "--model", "qwen3-coder",
            "--cwd", str(self.work), "--prompt", "Audit", "--dry-run", "--json",
        )
        self.assertEqual(res_c.returncode, 0, res_c.stderr)
        prev_c = json.loads(res_c.stdout)
        self.assertEqual(prev_c["harness"], "custom")
        self.assertIn("openrouter/qwen3-coder", prev_c["argv"])

    def test_run_enforces_approved_pool_writes_receipt_and_handles_timeout(self):
        _make_stub(
            self.stub_bin,
            "codex",
            'out=""\nprev=""\nfor a in "$@"; do\n  if [ "$prev" = "-o" ]; then out="$a"; fi\n  prev="$a"\ndone\n'
            'body=$(cat)\n'
            'msg="VECTOR: auth\nMODEL: openai/gpt-5.4 (high)\nVERDICT: BLOCKED: token replay\n"\n'
            'if [ -n "$out" ]; then printf "%s" "$msg" > "$out"; else printf "%s" "$msg"; fi\n',
        )
        _make_stub(self.stub_bin, "pi", 'echo "VECTOR: auth"; echo "MODEL: anthropic/claude-sonnet-4-6"; echo "VERDICT: CLEAR"\n')
        _make_stub(self.stub_bin, "devin", "sleep 5\n")

        settings = self.dir / "settings.json"
        settings.write_text(json.dumps({
            "reviewer_pool": [
                {"provider": "openai", "model": "gpt-5.4", "effort": "high", "harness": "codex"},
                {"provider": "anthropic", "model": "claude-sonnet-4-6", "effort": "medium", "harness": "pi"},
                {"provider": "devin", "model": "slow", "harness": "devin"},
            ]
        }))

        # Unapproved model -> exit 2, refuses dispatch
        denied = self.run_dispatch(
            "run", "--settings", str(settings), "--provider", "openai", "--model", "o3-unapproved",
            "--cwd", str(self.work), "--prompt", "Review",
        )
        self.assertEqual(denied.returncode, 2)
        self.assertIn("not in approved reviewer_pool", denied.stderr)

        # Approved Codex model -> writes report & structured receipt JSON
        out_codex = self.dir / "out" / "codex-review.md"
        ok_codex = self.run_dispatch(
            "run", "--settings", str(settings), "--provider", "openai", "--model", "gpt-5.4",
            "--vector", "auth", "--cwd", str(self.work), "--prompt", "Review auth.py",
            "--out", str(out_codex), "--json",
        )
        self.assertEqual(ok_codex.returncode, 0, ok_codex.stderr)
        payload = json.loads(ok_codex.stdout)
        self.assertEqual(payload["harness"], "codex")
        self.assertEqual(payload["vector"], "auth")
        self.assertIn("BLOCKED: token replay", out_codex.read_text())
        receipt_path = out_codex.with_suffix(".md.receipt.json")
        self.assertTrue(receipt_path.is_file())
        rec = json.loads(receipt_path.read_text())
        self.assertEqual(rec["provider"], "openai")
        self.assertEqual(rec["model"], "gpt-5.4")
        self.assertEqual(rec["exit_code"], 0)

        # Approved Pi model -> runs cleanly
        out_pi = self.dir / "out" / "pi-review.md"
        ok_pi = self.run_dispatch(
            "run", "--settings", str(settings), "--provider", "anthropic", "--model", "claude-sonnet-4-6",
            "--vector", "auth", "--cwd", str(self.work), "--prompt", "Review auth.py", "--out", str(out_pi),
        )
        self.assertEqual(ok_pi.returncode, 0, ok_pi.stderr)
        self.assertIn("VERDICT: CLEAR", out_pi.read_text())

        # Timeout terminates cleanly and marks timed_out=true in receipt
        out_slow = self.dir / "out" / "slow.md"
        to = self.run_dispatch(
            "run", "--settings", str(settings), "--provider", "devin", "--model", "slow",
            "--cwd", str(self.work), "--prompt", "Review", "--out", str(out_slow), "--timeout", "0.3", "--json",
        )
        self.assertEqual(to.returncode, 1)
        to_data = json.loads(to.stdout)
        self.assertTrue(to_data["timed_out"])


class MultiHarnessEvalRunnerTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="astack-eval-runner-test-"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.ev = _load_eval_module()

    def test_mount_and_prompt_adaptation_across_all_six_harnesses(self):
        settings = {
            "roles": {"worker": {"provider": "openai", "model": "gpt-5.4-mini", "effort": "medium"}},
            "reviewer_pool": [
                {"provider": "openai", "model": "gpt-5.4", "effort": "high", "harness": "codex"},
                {"provider": "anthropic", "model": "sonnet", "effort": "medium", "harness": "claude"},
            ],
        }
        base_prompt = "`/astack:go` Review repo. The worker built this change on `anthropic/haiku`."

        for harness in self.ev.SUPPORTED_HARNESSES:
            ws = self.dir / f"ws-{harness}"
            ws.mkdir()
            env_over, extra_args = self.ev.mount_harness_into_workspace(harness, ws, settings)
            self.assertIn("PATH", env_over)
            prompt = self.ev.adapt_prompt(base_prompt, harness, settings)
            self.assertIn("openai/gpt-5.4-mini", prompt)
            if harness != "claude":
                self.assertNotIn("/astack:go", prompt)
            if harness == "codex":
                self.assertIn("$astack-go", prompt)
                codex_agents = Path(env_over["CODEX_HOME"]) / "agents"
                # Only the Codex-routable OpenAI pool entry gets a .toml; cross-harness claude does not
                toml_files = sorted(p.name for p in codex_agents.glob("astack-reviewer*.toml"))
                self.assertEqual(toml_files, ["astack-reviewer-openai-gpt-5-4-high.toml"])
                parsed = tomllib.loads((codex_agents / toml_files[0]).read_text())
                self.assertEqual(parsed["model"], "gpt-5.4")
                self.assertEqual(parsed["model_reasoning_effort"], "high")
            elif harness == "agy":
                self.assertTrue((ws / ".agents/plugins/astack/plugin.json").is_file())
            elif harness == "cursor":
                self.assertTrue((ws / ".cursor/skills/astack-go/SKILL.md").is_file())
            elif harness in ("devin", "pi"):
                self.assertTrue((ws / ".agents/skills/astack-go/SKILL.md").is_file())
            elif harness == "claude":
                self.assertIn("--plugin-dir", extra_args)

    def test_parse_and_grade_canonical_events_across_codex_agy_pi_and_dispatch_receipts(self):
        codex_settings = self.ev.DEFAULT_HARNESS_SETTINGS["codex"]
        # Simulate Codex JSONL output: reads review/SKILL.md, spawns gpt-5.4 via spawn_agent,
        # and dispatches gpt-5.4-mini via astack-dispatch receipt on disk!
        codex_jsonl = "\n".join([
            json.dumps({"type": "item.completed", "item": {"type": "command_execution", "command": "cat .codex_home/skills/astack-review/SKILL.md"}}),
            json.dumps({"type": "item.completed", "item": {"type": "collab_tool_call", "tool": "spawn_agent", "agent_type": "astack-reviewer-openai-gpt-5-4-medium"}}),
            json.dumps({"type": "item.completed", "item": {"type": "command_execution", "command": "astack-review-ledger --markdown < ledger.json"}}),
            json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "## Coverage map\nrisky gpt-5.4 gpt-5.4-mini\nNOT ASSIGNED\nPOOL EXHAUSTED\nCOULD NOT TEST"}}),
        ])
        ws = self.dir / "codex-ws"
        ws.mkdir()
        (ws / "review-mini.md.receipt.json").write_text(json.dumps({
            "role": "reviewer",
            "provider": "openai",
            "model": "gpt-5.4-mini",
            "harness": "codex",
            "argv": ["codex", "exec", "--model", "gpt-5.4-mini"],
            "exit_code": 0,
        }))

        final_text, events = self.ev.parse_harness_events("codex", codex_jsonl, workspace=ws, settings=codex_settings)
        self.assertIn("Coverage map", final_text)

        ok_read, _ = self.ev.evaluate_tool_grader({"tool": "Read", "input_match": "review/SKILL\\.md", "min": "1"}, events, codex_settings)
        self.assertTrue(ok_read)
        ok_two, _ = self.ev.evaluate_tool_grader({"tool": "Agent", "input_match": "astack:reviewer", "min": "2"}, events, codex_settings)
        self.assertTrue(ok_two)
        ok_non_worker, _ = self.ev.evaluate_tool_grader(
            {"tool": "Agent", "input_match": '"subagent_type":"astack:reviewer".*"model":"sonnet"', "min": "1"},
            events,
            codex_settings,
        )
        self.assertTrue(ok_non_worker)
        ok_worker, _ = self.ev.evaluate_tool_grader(
            {"tool": "Agent", "input_match": '"subagent_type":"astack:reviewer".*"model":"haiku"', "min": "1"},
            events,
            codex_settings,
        )
        self.assertTrue(ok_worker)
        ok_no_gp, _ = self.ev.evaluate_tool_grader(
            {"tool": "Agent", "input_match": "general-purpose", "min": "0", "max": "0"},
            events,
            codex_settings,
        )
        self.assertTrue(ok_no_gp)

        # Simulate Pi JSON stream dispatching cross-harness reviewers via astack-dispatch
        pi_jsonl = "\n".join([
            json.dumps({"type": "tool_execution_start", "toolName": "read", "args": {"path": ".agents/skills/astack-review/SKILL.md"}}),
            json.dumps({"type": "tool_execution_start", "toolName": "bash", "args": {"command": "astack-dispatch run --provider anthropic --model claude-sonnet-4-6 --harness pi --cwd repo"}}),
            json.dumps({"type": "message_end", "message": {"content": [{"type": "text", "text": "## Coverage map\nlow claude-sonnet-4-6"}]}}),
        ])
        pi_settings = self.ev.DEFAULT_HARNESS_SETTINGS["pi"]
        pi_text, pi_events = self.ev.parse_harness_events("pi", pi_jsonl, settings=pi_settings)
        self.assertIn("Coverage map", pi_text)
        ok_pi_one, _ = self.ev.evaluate_tool_grader({"tool": "Agent", "input_match": "astack:reviewer", "min": "1", "max": "1"}, pi_events, pi_settings)
        self.assertTrue(ok_pi_one)
        ok_pi_non_worker, _ = self.ev.evaluate_tool_grader(
            {"tool": "Agent", "input_match": '"subagent_type":"astack:reviewer".*"model":"sonnet"', "min": "1", "max": "1"},
            pi_events,
            pi_settings,
        )
        self.assertTrue(ok_pi_non_worker)
        ok_pi_no_worker, _ = self.ev.evaluate_tool_grader(
            {"tool": "Agent", "input_match": '"subagent_type":"astack:reviewer".*"model":"haiku"', "min": "0", "max": "0"},
            pi_events,
            pi_settings,
        )
        self.assertTrue(ok_pi_no_worker)

        # Simulate Antigravity's REAL stream-json schema (`event: step_update` / `event: result`)
        agy_jsonl = "\n".join([
            json.dumps({"event": "init", "init": {"tools": ["read_file", "run_command", "invoke_subagent"]}}),
            json.dumps({
                "event": "step_update",
                "step_update": {
                    "state": "DONE",
                    "step_type": "tool",
                    "tool_name": "read_file",
                    "tool_info": {"name": "read_file", "parameters": {"Path": ".agents/plugins/astack/skills/no-implicit-states/SKILL.md"}},
                },
            }),
            json.dumps({
                "event": "step_update",
                "step_update": {
                    "state": "DONE",
                    "step_type": "tool",
                    "tool_name": "invoke_subagent",
                    "tool_info": {"name": "invoke_subagent", "parameters": {"TypeName": "astack-reviewer", "Model": "gemini-2.5-pro"}},
                },
            }),
            json.dumps({"event": "result", "result": {"status": "SUCCESS", "response": "Refactored with explicit enum states."}}),
        ])
        agy_text, agy_events = self.ev.parse_harness_events("agy", agy_jsonl)
        self.assertEqual(agy_text, "Refactored with explicit enum states.")
        ok_agy_read, _ = self.ev.evaluate_tool_grader({"tool": "Read", "input_match": "no-implicit-states/SKILL\\.md", "min": "1"}, agy_events)
        self.assertTrue(ok_agy_read)
        ok_agy_rev, _ = self.ev.evaluate_tool_grader({"tool": "Agent", "input_match": "astack:reviewer", "min": "1"}, agy_events)
        self.assertTrue(ok_agy_rev)

        # Simulate Codex session rollout JSONL harvesting (deduplicated by payload.id across root + child rollouts)
        rollout_ws = self.dir / "codex-rollout-ws"
        sess_dir = rollout_ws / ".codex_home" / "sessions" / "2026" / "11" / "24"
        sess_dir.mkdir(parents=True)
        spawn_line = json.dumps({
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "status": "completed",
                "id": "fc_unique_123",
                "name": "spawn_agent",
                "arguments": json.dumps({"task_name": "rev", "agent_type": "astack-reviewer-openai-gpt-5-4-medium", "message": "..."}),
            },
        })
        (sess_dir / "rollout-parent.jsonl").write_text(spawn_line + "\n")
        (sess_dir / "rollout-child.jsonl").write_text(spawn_line + "\n")  # duplicated in child fork
        _, r_events = self.ev.parse_harness_events("codex", "", workspace=rollout_ws, settings=codex_settings)
        ok_roll_one, _ = self.ev.evaluate_tool_grader({"tool": "Agent", "input_match": "astack:reviewer", "min": "1", "max": "1"}, r_events, codex_settings)
        self.assertTrue(ok_roll_one)
        ok_roll_mod, _ = self.ev.evaluate_tool_grader({"tool": "Agent", "input_match": '"subagent_type":"astack:reviewer".*"model":"sonnet"', "min": "1", "max": "1"}, r_events, codex_settings)
        self.assertTrue(ok_roll_mod)

    def test_install_agents_installs_all_four_full_agents_for_every_harness(self):
        settings = self.dir / "settings.json"
        settings.write_text(json.dumps({
            "roles": {
                "lead": {"provider": "anthropic", "model": "opus", "effort": "high"},
                "worker": {"provider": "openai", "model": "gpt-6.2-astra", "effort": "medium"},
                "researcher": {"provider": "google", "model": "gemini-2.5-pro", "effort": "high"},
            },
            "reviewer_pool": [
                {"provider": "openai", "model": "gpt-6.2-astra", "effort": "high", "harness": "codex"},
                {"provider": "anthropic", "model": "sonnet", "effort": "medium", "harness": "claude"},
            ],
        }))

        # Codex: installs astack-lead, astack-worker, astack-researcher + per-model astack-reviewer-<slug>.toml
        codex_dir = self.dir / "codex-agents"
        r_cx = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "install-agents", "--harness", "codex", "--settings", str(settings), "--target", str(codex_dir)],
            capture_output=True, text=True,
        )
        self.assertEqual(r_cx.returncode, 0, r_cx.stderr)
        cx_files = sorted(p.name for p in codex_dir.glob("*.toml"))
        self.assertEqual(cx_files, [
            "astack-lead.toml",
            "astack-researcher.toml",
            "astack-reviewer-openai-gpt-6-2-astra-high.toml",
            "astack-worker.toml",
        ])
        parsed_rev = tomllib.loads((codex_dir / "astack-reviewer-openai-gpt-6-2-astra-high.toml").read_text())
        self.assertEqual(parsed_rev["model"], "gpt-6.2-astra")
        self.assertEqual(parsed_rev["model_reasoning_effort"], "high")

        # Antigravity, Cursor, Devin, Pi, Claude: all 4 native .md agents installed with harness-native frontmatter
        for h, must_contain in (
            ("antigravity", ("subagent: true", "mainAgent: true")),
            ("cursor", ("is_background: true",)),
            ("devin", ("name: astack-lead",)),
            ("pi", ("readOnly: true", "promptSnippet:")),
            ("claude", ("disallowedTools:",)),
        ):
            out_dir = self.dir / f"agents-{h}"
            res = subprocess.run(
                [sys.executable, "-B", str(BIN / "astack-tools"), "install-agents", "--harness", h, "--settings", str(settings), "--target", str(out_dir)],
                capture_output=True, text=True,
            )
            self.assertEqual(res.returncode, 0, f"{h}: {res.stderr}")
            md_files = sorted(p.name for p in out_dir.glob("*.md"))
            self.assertEqual(md_files, ["astack-lead.md", "astack-researcher.md", "astack-reviewer.md", "astack-worker.md"], h)
            joined = "\n".join((out_dir / f).read_text() for f in md_files)
            for token in must_contain:
                self.assertIn(token, joined, f"{h} missing {token!r}")


if __name__ == "__main__":
    unittest.main()
