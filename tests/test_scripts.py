"""Behaviour tests for astack's scripts: what a lead or a hook sees when it runs them."""
import json
import os
import platform
import random
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent / "bin"
MARKER = "<!-- astack lane log -->"


def run(script, *args, stdin=None, cwd=None, cache=None):
    env = {**os.environ, "XDG_CACHE_HOME": str(cache)} if cache else None
    command = [str(BIN / script)] if script.endswith("-hook") else [sys.executable, str(BIN / script)]
    return subprocess.run([*command, *args], capture_output=True, text=True, input=stdin, cwd=cwd, env=env)


def git(repo, *args):
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid", "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "commit.gpgsign", "GIT_CONFIG_VALUE_0": "false"}
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env=env)
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


def commit(repo, name, text):
    (Path(repo) / name).write_text(text)
    git(repo, "add", name)
    git(repo, "commit", "-q", "-m", f"change {name}")
    return git(repo, "rev-parse", "HEAD")


def stamp_at(minutes_from_now):
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes_from_now)).strftime("%Y-%m-%dT%H:%MZ")


class Scratch(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="astack-test-"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)


class StampTest(Scratch):
    def log(self, body):
        path = self.dir / "LANES.md"
        path.write_text(f"{MARKER}\n# p lane log\n\n## Line formats\n\nstarted <worker> on <lane>\n\n## Log\n\n{body}")
        return path

    def test_stamps_only_new_log_lines(self):
        path = self.log("2026-11-23T14:02Z started a on x (1)\nsteer a: stop the A/B\n")
        self.assertEqual(run("astack-stamp", str(path)).returncode, 0)
        lines = path.read_text().splitlines()
        self.assertIn("started <worker> on <lane>", lines)
        self.assertEqual(lines[-2], "2026-11-23T14:02Z started a on x (1)")
        self.assertRegex(lines[-1], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z steer a: stop the A/B$")

    def test_running_twice_changes_nothing(self):
        path = self.log("ended a: NOT MERGED\n")
        run("astack-stamp", str(path))
        once = path.read_text()
        run("astack-stamp", str(path))
        self.assertEqual(path.read_text(), once)

    def test_leaves_files_without_the_marker_alone(self):
        path = self.dir / "LANES.md"
        path.write_text("# someone else's log\n\n## Log\n\nhand-written line\n")
        before = path.read_text()
        run("astack-stamp", str(path))
        self.assertEqual(path.read_text(), before)

    def test_hook_stamps_an_edited_lane_log(self):
        path = self.log("ended a: MERGED abc\n")
        event = {"tool_name": "Edit", "tool_input": {"file_path": str(path)}, "cwd": str(self.dir)}
        self.assertEqual(run("astack-stamp", "--hook", stdin=json.dumps(event)).returncode, 0)
        self.assertRegex(path.read_text().splitlines()[-1], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z ended a: MERGED abc$")

    def test_hook_stamps_a_lane_log_appended_from_the_shell(self):
        path = self.log("closed x: done\n")
        event = {"tool_name": "Bash", "tool_input": {"command": "echo 'closed x: done' >> LANES.md"},
                 "cwd": str(self.dir)}
        run("astack-stamp", "--hook", stdin=json.dumps(event))
        self.assertRegex(path.read_text().splitlines()[-1], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z closed x: done$")

    def test_the_hook_entry_point_stamps_through_the_filter(self):
        path = self.log("finding a: the old parser leaks\n")
        event = {"tool_name": "Write", "tool_input": {"file_path": str(path)}}
        self.assertEqual(run("astack-stamp-hook", stdin=json.dumps(event)).returncode, 0)
        self.assertRegex(path.read_text().splitlines()[-1], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z finding a: ")

    def test_the_hook_entry_point_passes_other_events_through(self):
        other = self.dir / "notes.md"
        other.write_text("plain\n")
        event = {"tool_name": "Write", "tool_input": {"file_path": str(other)}}
        self.assertEqual(run("astack-stamp-hook", stdin=json.dumps(event)).returncode, 0)
        self.assertEqual(other.read_text(), "plain\n")

    def test_a_copy_of_the_lane_log_template_is_stamped(self):
        template = Path(__file__).resolve().parent.parent / "skills" / "lead" / "templates" / "LANES.md"
        path = self.dir / "LANES.md"
        path.write_text(template.read_text() + "steer a: stop\n")
        run("astack-stamp", str(path))
        text = path.read_text()
        self.assertRegex(text.splitlines()[-1], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z steer a: stop$")
        self.assertIn("    started <worker> on <lane>", text)

    def test_hook_ignores_events_for_other_files(self):
        other = self.dir / "notes.md"
        other.write_text("plain\n")
        event = {"tool_name": "Write", "tool_input": {"file_path": str(other)}}
        self.assertEqual(run("astack-stamp", "--hook", stdin=json.dumps(event)).returncode, 0)
        self.assertEqual(other.read_text(), "plain\n")


class StatusTest(Scratch):
    def setUp(self):
        super().setUp()
        self.repo = self.dir / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        commit(self.repo, "a.txt", "a")
        git(self.repo, "branch", "lane/search")

    def write_log(self, lines):
        path = self.dir / "prog" / "LANES.md"
        path.parent.mkdir()
        path.write_text(f"{MARKER}\n# prog lane log\n\nRepository: {self.repo}\n\n## Log\n\n" + "\n".join(lines) + "\n")
        return path

    def test_shows_running_workers_with_their_clocks_and_commits(self):
        path = self.write_log([
            f"{stamp_at(-50)} started search-1 on search (a1) | branch lane/search | wind-down {stamp_at(5)} | ends {stamp_at(10)} | deliverable: d | done when: e",
            f"{stamp_at(-70)} started ingest-1 on ingest (b1) | branch lane/ingest | wind-down {stamp_at(-15)} | ends {stamp_at(-10)} | deliverable: d | done when: e",
            f"{stamp_at(-90)} started old-1 on old (c1) | branch lane/old | wind-down {stamp_at(-35)} | ends {stamp_at(-30)} | deliverable: d | done when: e",
            f"{stamp_at(-31)} ended old-1: MERGED 123 (verified)",
            f"{stamp_at(-30)} closed old: done",
        ])
        result = run("astack-status", str(path))
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout
        self.assertIn("search-1 on search (agent a1)", out)
        self.assertRegex(out, r"wind-down \d\d:\d\dZ \(in \d+m\)")
        self.assertIn("lane/search: last commit", out)
        self.assertIn("ingest-1 on ingest", out)
        self.assertRegex(out, r"ends \d\d:\d\dZ \(PAST by \d+m\)")
        self.assertIn("lane/ingest: no commits found", out)
        self.assertNotIn("old-1 on old", out)
        self.assertRegex(out, r"old: closed .*, 1 worker\n")

    def test_lists_questions_the_person_has_not_answered(self):
        path = self.write_log([
            f"{stamp_at(-20)} asked: \"Keep the old export format?\"",
            f"{stamp_at(-15)} person: \"No\" -> export-2 told",
            f"{stamp_at(-5)} asked: \"Ship the faster parser now?\"",
        ])
        out = run("astack-status", str(path)).stdout
        self.assertIn("Ship the faster parser now?", out)
        self.assertNotIn("Keep the old export format?", out)

    def test_reads_a_successor_line_from_the_template_format(self):
        path = self.write_log([
            f"{stamp_at(-2)} started search-2 on search (a2) | successor of search-1 | branch lane/search | wind-down {stamp_at(53)} | ends {stamp_at(58)} | deliverable: d | done when: e",
        ])
        out = run("astack-status", str(path)).stdout
        self.assertIn("search-2 on search (agent a2, successor of search-1)", out)

    def test_one_line_summary(self):
        path = self.write_log([
            f"{stamp_at(-50)} started a-1 on a (x) | branch lane/search | wind-down {stamp_at(5)} | ends {stamp_at(10)} | deliverable: d | done when: e",
            f"{stamp_at(-70)} started b-1 on b (y) | branch lane/b | wind-down {stamp_at(-15)} | ends {stamp_at(-10)} | deliverable: d | done when: e",
            f"{stamp_at(-1)} asked: \"Which?\"",
        ])
        line = run("astack-status", str(path), "--line").stdout.strip()
        self.assertRegex(line, r"^astack prog: 2 running · next end \d\d:\d\dZ \(\d+m\) · 1 past limit · 1 waiting on you$")


class VerifyMergeTest(Scratch):
    def setUp(self):
        super().setUp()
        self.origin = self.dir / "origin.git"
        git(self.dir, "init", "-q", "--bare", "-b", "main", str(self.origin))
        self.repo = self.dir / "clone"
        git(self.dir, "clone", "-q", str(self.origin), str(self.repo))
        git(self.repo, "checkout", "-q", "-b", "main")
        self.merged = commit(self.repo, "ok.txt", "ok")
        git(self.repo, "push", "-q", "origin", "main")
        git(self.repo, "checkout", "-q", "-b", "lane/x")
        self.unmerged = commit(self.repo, "wip.txt", "wip")

    def verify(self, *args):
        return run("astack-verify-merge", *args, "--repo", str(self.repo), cache=self.dir / "cache")

    def test_a_merged_commit_is_verified(self):
        result = self.verify(self.merged)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(result.stdout.startswith(f"VERIFIED: {self.merged[:12]} is on origin/main"))
        self.assertIn("ok.txt", result.stdout)

    def test_a_commit_only_on_its_branch_is_not_verified(self):
        result = self.verify(self.unmerged)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(result.stdout.startswith(f"NOT VERIFIED: {self.unmerged[:12]} is not on origin/main"))

    def test_an_unknown_commit_is_not_verified(self):
        result = self.verify("0123456789abcdef0123456789abcdef01234567")
        self.assertEqual(result.returncode, 1)
        self.assertTrue(result.stdout.startswith("NOT VERIFIED:"))

    def test_a_merge_pushed_after_the_last_fetch_is_found(self):
        other = self.dir / "other"
        git(self.dir, "clone", "-q", str(self.origin), str(other))
        late = commit(other, "late.txt", "late")
        git(other, "push", "-q", "origin", "main")
        result = self.verify(late)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_a_check_that_passes_and_one_that_fails(self):
        passing = self.verify(self.merged, "--check", "test -f ok.txt")
        self.assertEqual(passing.returncode, 0, passing.stdout)
        self.assertIn("check passed", passing.stdout)
        failing = self.verify(self.merged, "--check", "test -f wip.txt")
        self.assertEqual(failing.returncode, 1)
        self.assertTrue(failing.stdout.startswith("NOT VERIFIED:"))
        self.assertIn("check failed, exit 1", failing.stdout)

    def test_a_missing_target_cannot_be_checked(self):
        result = self.verify(self.merged, "--target", "origin/nope")
        self.assertEqual(result.returncode, 2)
        self.assertTrue(result.stdout.startswith("NOT CHECKED:"))


class DecisionsTest(Scratch):
    def write_log(self, lines):
        path = self.dir / "prog" / "LANES.md"
        path.parent.mkdir()
        path.write_text(f"{MARKER}\n# prog lane log\n\n## Log\n\n" + "\n".join(lines) + "\n")
        return path

    def test_lists_decided_lines_and_person_directives(self):
        path = self.write_log([
            "2026-11-23T10:00Z started w1 on api (a1) | branch lane/api",
            "2026-11-23T10:15Z decided: JSON vs CBOR -> CBOR (settled by an A/B; evidence: bench/cbor.md)",
            "2026-11-23T10:30Z person: \"Keep backward-compatible CLI flags\" -> w1 told",
            "2026-11-23T11:00Z decided: retry strategy -> exponential backoff (settled by research; evidence: RFC 9110)",
        ])
        result = run("astack-decisions", str(path))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("JSON vs CBOR -> CBOR (settled by an A/B; evidence: bench/cbor.md)", result.stdout)
        self.assertIn('[person] "Keep backward-compatible CLI flags" -> w1 told', result.stdout)
        self.assertIn("retry strategy -> exponential backoff", result.stdout)

    def test_filters_by_query_settled_by_since_and_json(self):
        path = self.write_log([
            "2026-11-23T10:15Z decided: JSON vs CBOR -> CBOR (settled by an A/B; evidence: bench/cbor.md)",
            "2026-11-23T10:30Z person: \"Keep backward-compatible CLI flags\" -> w1 told",
            "2026-11-23T11:00Z decided: retry strategy -> exponential backoff (settled by research; evidence: RFC 9110)",
        ])
        by_source = run("astack-decisions", str(path), "--settled-by", "A/B", "--json")
        self.assertEqual(by_source.returncode, 0, by_source.stderr)
        items = json.loads(by_source.stdout)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["choice"], "CBOR")

        since = run("astack-decisions", str(path), "--since", "2026-11-23T10:30Z", "--json")
        self.assertEqual(since.returncode, 0, since.stderr)
        self.assertEqual([i["kind"] for i in json.loads(since.stdout)], ["person", "decided"])

        query = run("astack-decisions", str(path), "--query", "rfc 9110", "--json")
        self.assertEqual(len(json.loads(query.stdout)), 1)

    def test_missing_log_exits_one_and_bad_since_exits_two(self):
        missing = run("astack-decisions", str(self.dir / "nope"))
        self.assertEqual(missing.returncode, 1)
        bad = run("astack-decisions", str(self.dir), "--since", "not-a-date")
        self.assertEqual(bad.returncode, 2)


class ToolsTest(Scratch):
    def test_doctor_reports_missing_venv_and_exits_one(self):
        venv = self.dir / "venv"
        result = run("astack-tools", "doctor", "--venv", str(venv), "--json")
        self.assertEqual(result.returncode, 1, result.stderr)
        data = json.loads(result.stdout)
        self.assertFalse(data["venv_exists"])
        self.assertFalse(data["core_ready"])
        self.assertIsNone(data["packages"]["taskex"])
        self.assertIsNone(data["packages"]["orchestral"])
        self.assertIsNone(data["packages"]["werkflow"])
        self.assertEqual(
            data["capabilities"],
            {"taskex_checkpoints": False, "orchestral_dag": False, "orchestral_checkpoints": False},
        )
        self.assertIn("compatible_python", data)

    def test_doctor_detects_taskex_and_orchestral_capabilities(self):
        venv = self.dir / "cap-venv"
        subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)], check=True)
        site = next((venv / "lib").glob("python*/site-packages"))

        def write_pkg(name, version, body):
            (site / f"{name}.py").write_text(body)
            dist = site / f"{name}-{version}.dist-info"
            dist.mkdir()
            (dist / "METADATA").write_text(f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n")

        write_pkg("taskex", "0.2.16", "TaskRunner = object\n")
        write_pkg("orchestral", "0.1.2", "Orchestral = object\n")
        write_pkg("werkflow", "0.1.0", "Workflow = object\n")

        old_json = run("astack-tools", "doctor", "--venv", str(venv), "--json")
        self.assertEqual(old_json.returncode, 0, old_json.stderr)
        self.assertEqual(
            json.loads(old_json.stdout)["capabilities"],
            {"taskex_checkpoints": False, "orchestral_dag": False, "orchestral_checkpoints": False},
        )
        old_text = run("astack-tools", "doctor", "--venv", str(venv))
        self.assertIn("missing checkpoints/pause-resume", old_text.stdout)
        self.assertIn("missing DAG waves & checkpoints + pause/resume", old_text.stdout)

        # orchestral 0.3.0: DAG waves without checkpoints/pause-resume
        (site / "taskex.py").write_text("SQLiteCheckpointStore = checkpoint = pause_point = object\n")
        (site / "orchestral.py").write_text("build_execution_plan = OrchestralCycleError = object\n")
        mid_json = run("astack-tools", "doctor", "--venv", str(venv), "--json")
        self.assertEqual(
            json.loads(mid_json.stdout)["capabilities"],
            {"taskex_checkpoints": True, "orchestral_dag": True, "orchestral_checkpoints": False},
        )
        mid_text = run("astack-tools", "doctor", "--venv", str(venv))
        self.assertIn("DAG waves; missing checkpoints + pause/resume", mid_text.stdout)

        # orchestral 0.4.0: DAG waves + checkpoints/pause-resume
        (site / "orchestral.py").write_text(
            "build_execution_plan = OrchestralCycleError = SQLiteCheckpointStore = checkpoint = pause_point = object\n"
            "class WorkflowStatus:\n    PAUSED = 'PAUSED'\n"
            "class Orchestral:\n    pause = resume = pause_step = resume_step = object\n"
        )
        new_json = run("astack-tools", "doctor", "--venv", str(venv), "--json")
        self.assertEqual(new_json.returncode, 0, new_json.stderr)
        self.assertEqual(
            json.loads(new_json.stdout)["capabilities"],
            {"taskex_checkpoints": True, "orchestral_dag": True, "orchestral_checkpoints": True},
        )
        new_text = run("astack-tools", "doctor", "--venv", str(venv))
        self.assertIn("checkpoints + pause/resume", new_text.stdout)
        self.assertIn("DAG waves, checkpoints + pause/resume", new_text.stdout)
        self.assertNotIn("upgrade taskex/orchestral", new_text.stdout)

        env_out = run("astack-tools", "env", "--venv", str(venv))
        self.assertEqual(env_out.returncode, 0, env_out.stderr)
        self.assertIn(f"export VIRTUAL_ENV={venv}", env_out.stdout)
        self.assertIn(f"export PATH={venv / 'bin'}:", env_out.stdout)

        ps_out = run("astack-tools", "env", "--venv", str(venv), "--shell", "powershell")
        self.assertEqual(ps_out.returncode, 0, ps_out.stderr)
        self.assertIn(f"$env:VIRTUAL_ENV = '{venv}'", ps_out.stdout)
        self.assertIn("$env:PATH =", ps_out.stdout)

        cmd_out = run("astack-tools", "env", "--venv", str(venv), "--shell", "cmd")
        self.assertEqual(cmd_out.returncode, 0, cmd_out.stderr)
        self.assertIn(f'set "VIRTUAL_ENV={venv}"', cmd_out.stdout)

    def test_all_bin_python_scripts_work_under_system_python3_and_find_uv_outside_path(self):
        interpreters = [sys.executable]
        if Path("/usr/bin/python3").is_file() and str(Path("/usr/bin/python3").resolve()) != str(Path(sys.executable).resolve()):
            interpreters.append("/usr/bin/python3")

        py_scripts = [p for p in sorted(BIN.iterdir()) if p.is_file() and p.read_text().startswith("#!/usr/bin/env python3")]
        self.assertGreaterEqual(len(py_scripts), 5)

        fake_home = self.dir / "home"
        bin_home = fake_home / ".local" / "bin"
        bin_home.mkdir(parents=True)
        uv_path = bin_home / "uv"
        uv_path.write_text("#!/bin/sh\nif [ \"$1\" = \"python\" ] && [ \"$2\" = \"find\" ]; then echo /fake/py312; exit 0; fi\nexit 0\n")
        uv_path.chmod(0o755)
        for cli in ("claude", "codex", "agy"):
            stub = bin_home / cli
            stub.write_text("#!/bin/sh\nexit 0\n")
            stub.chmod(0o755)
        stripped_env = {"HOME": str(fake_home), "PATH": "/usr/bin:/bin"}

        for py in interpreters:
            for script in py_scripts:
                if script.name == "astack-stamp":
                    res = subprocess.run(
                        [py, "-B", "-c", "import pathlib, sys; compile(pathlib.Path(sys.argv[1]).read_text(), sys.argv[1], 'exec')", str(script)],
                        capture_output=True, text=True,
                    )
                else:
                    res = subprocess.run([py, "-B", str(script), "--help"], capture_output=True, text=True)
                self.assertEqual(res.returncode, 0, f"{py} {script.name}: {res.stderr}")

            # Verify astack-tools doctor runs cleanly even under macOS /usr/bin/python3 (3.9)
            # AND discovers ~/.local/bin/uv and agent harnesses even when PATH is stripped!
            doc = subprocess.run(
                [py, str(BIN / "astack-tools"), "doctor", "--venv", str(self.dir / "missing-venv"), "--json"],
                capture_output=True, text=True, env=stripped_env,
            )
            self.assertEqual(doc.returncode, 1, doc.stderr)
            data = json.loads(doc.stdout)
            self.assertEqual(data["uv"], str(uv_path), f"{py} missed ~/.local/bin/uv")
            self.assertEqual(data["compatible_python"], "/fake/py312")
            self.assertIn(data["arch"], ("arm64", "amd64", platform.machine().lower()))
            self.assertEqual(data["harnesses"]["claude"]["provider"], "anthropic")
            self.assertEqual(data["harnesses"]["codex"]["provider"], "openai")
            self.assertEqual(data["harnesses"]["agy"]["provider"], "google")

    def test_link_bin_installs_scripts_idempotently_and_supports_copy(self):
        bin_dir = self.dir / "user-bin"
        first = run("astack-tools", "link-bin", "--bin-dir", str(bin_dir))
        self.assertEqual(first.returncode, 0, first.stderr)
        for name in ("astack-tools", "astack-status", "astack-decisions", "astack-verify-merge", "astack-check-gates", "astack-statechart", "astack-stamp"):
            linked = bin_dir / name
            self.assertTrue(linked.is_symlink(), f"missing symlink {linked}")
            self.assertEqual(linked.resolve(), (BIN / name).resolve())

        # Re-running is idempotent
        second = run("astack-tools", "link-bin", "--bin-dir", str(bin_dir))
        self.assertEqual(second.returncode, 0, second.stderr)

        # --copy mode writes executable copies
        copy_dir = self.dir / "user-bin-copy"
        copied = run("astack-tools", "link-bin", "--bin-dir", str(copy_dir), "--copy")
        self.assertEqual(copied.returncode, 0, copied.stderr)
        self.assertTrue((copy_dir / "astack-tools").is_file())
        self.assertFalse((copy_dir / "astack-tools").is_symlink())

    def test_install_provisions_python_via_uv_when_missing(self):
        fake_bin = self.dir / "fake-bin"
        fake_bin.mkdir()
        uv_stub = fake_bin / "uv"
        uv_stub.write_text("#!/bin/sh\nif [ \"$1\" = \"python\" ] && [ \"$2\" = \"find\" ]; then exit 1; fi\nexit 0\n")
        uv_stub.chmod(0o755)
        venv = self.dir / "uv-venv"
        env = {**os.environ, "PATH": f"{fake_bin}:{os.environ.get('PATH', '')}"}
        res = subprocess.run(
            [sys.executable, str(BIN / "astack-tools"), "install", "--venv", str(venv), "--profile", "core", "--dry-run"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        lines = res.stdout.strip().splitlines()
        self.assertEqual(len(lines), 3, res.stdout)
        self.assertIn("uv python install 3.12", lines[0])
        self.assertIn(f"uv venv {venv} --python 3.12", lines[1])
        self.assertIn("uv pip install", lines[2])

        # When uv python find succeeds, skip `uv python install`
        uv_stub.write_text("#!/bin/sh\nif [ \"$1\" = \"python\" ] && [ \"$2\" = \"find\" ]; then echo /fake/py312; exit 0; fi\nexit 0\n")
        res2 = subprocess.run(
            [sys.executable, str(BIN / "astack-tools"), "install", "--venv", str(venv), "--profile", "core", "--dry-run"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(res2.returncode, 0, res2.stderr)
        lines2 = res2.stdout.strip().splitlines()
        self.assertEqual(len(lines2), 2, res2.stdout)
        self.assertNotIn("uv python install", res2.stdout)
        self.assertIn(f"uv venv {venv} --python >=3.11", lines2[0])

    def test_install_dry_run_resolves_profiles_modules_and_github(self):
        venv = self.dir / "venv"
        core = run("astack-tools", "install", "--venv", str(venv), "--profile", "core", "--dry-run")
        self.assertEqual(core.returncode, 0, core.stderr)
        self.assertIn("taskex>=0.5.0 orchestral>=0.4.0 werkflow>=0.4.0", core.stdout)
        self.assertNotIn("werkflow-shell", core.stdout)

        all_prof = run("astack-tools", "install", "--venv", str(venv), "--profile", "all", "--dry-run")
        self.assertEqual(all_prof.returncode, 0, all_prof.stderr)
        self.assertIn("werkflow-metrikflow>=0.3.1", all_prof.stdout)
        self.assertNotIn("werkflow-metrik ", all_prof.stdout)
        self.assertIn("werkflow-docker>=0.4.1", all_prof.stdout)

        extra = run("astack-tools", "install", "--venv", str(venv), "--profile", "core", "--modules", "docker,jira", "--dry-run")
        self.assertEqual(extra.returncode, 0, extra.stderr)
        self.assertIn("werkflow-docker>=0.4.1", extra.stdout)
        self.assertIn("werkflow-jira", extra.stdout)

        gh = run("astack-tools", "install", "--venv", str(venv), "--profile", "core", "--modules", "shell", "--from-github", "--dry-run")
        self.assertEqual(gh.returncode, 0, gh.stderr)
        self.assertIn("git+https://github.com/adalundhe/taskex.git", gh.stdout)
        self.assertIn("git+https://github.com/adalundhe/orchestral.git", gh.stdout)
        self.assertIn("git+https://github.com/adalundhe/werkflow.git", gh.stdout)
        self.assertIn("werkflow-modules.git#subdirectory=werkflow-shell", gh.stdout)
        self.assertIn("werkflow-modules.git#subdirectory=werkflow-core", gh.stdout)

    def test_unknown_module_exits_two_and_missing_exec_or_env_exits_one(self):
        venv = self.dir / "venv"
        bad = run("astack-tools", "install", "--venv", str(venv), "--modules", "nope", "--dry-run")
        self.assertEqual(bad.returncode, 2)
        missing_py = run("astack-tools", "python", "--venv", str(venv), "-c", "print(1)")
        self.assertEqual(missing_py.returncode, 1)
        missing_env = run("astack-tools", "env", "--venv", str(venv))
        self.assertEqual(missing_env.returncode, 1)
        path_res = run("astack-tools", "path", "--venv", str(venv))
        self.assertEqual(path_res.returncode, 0)
        self.assertTrue(path_res.stdout.strip().endswith("/python"))


def _has_real_tlc():
    if shutil.which("tlc"):
        return True
    if not shutil.which("java"):
        return False
    candidates = [
        Path(os.environ["TLA2TOOLS_JAR"]).expanduser() if os.environ.get("TLA2TOOLS_JAR") else None,
        Path("/opt/homebrew/share/tla+/tla2tools.jar"),
        Path("/usr/local/share/tla+/tla2tools.jar"),
        Path.home() / ".local" / "share" / "tla+" / "tla2tools.jar",
        Path("/Applications/TLA+ Toolbox.app/Contents/Eclipse/tla2tools.jar"),
    ]
    return any(p is not None and p.is_file() for p in candidates)


def _dot_escape(text):
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _independent_min_hops(initial_ids, edges, target_id):
    """Independent BFS oracle for verifying shortest-path distances."""
    adj = {}
    for src, dst in edges:
        adj.setdefault(src, []).append(dst)
    dist = {}
    q = deque()
    for init in initial_ids:
        if init not in dist:
            dist[init] = 0
            q.append(init)
    while q:
        cur = q.popleft()
        if cur == target_id:
            return dist[cur]
        for nxt in adj.get(cur, ()):
            if nxt not in dist:
                dist[nxt] = dist[cur] + 1
                q.append(nxt)
    return -1


class StatechartTest(Scratch):
    def test_render_dot_finds_shortest_path_to_each_broken_invariant_and_draws_mermaid(self):
        dot = self.dir / "states.dot"
        dot.write_text(
            'digraph DiskGraph {\n'
            '  -1001 [label="/\\\\ x = 0\\n/\\\\ y = 0", style = filled];\n'
            '  2002 [label="/\\\\ x = 1\\n/\\\\ y = 0"];\n'
            '  3003 [label="/\\\\ x = 2\\n/\\\\ y = 0"];\n'
            '  4004 [label="/\\\\ x = 3\\n/\\\\ y = 1", color=red, invariant="InvA"];\n'
            '  5005 [label="/\\\\ x = 0\\n/\\\\ y = 9", color=red, invariant="InvB"];\n'
            '  6006 [label="isolated bad", color=red, invariant="InvUnreachable"];\n'
            '  -1001 -> 2002 [label="Slow1"];\n'
            '  2002 -> 3003 [label="Slow2"];\n'
            '  3003 -> 4004 [label="Slow3"];\n'
            '  -1001 -> 4004 [label="Shortcut"];\n'
            '  2002 -> 5005 [label="BreakB"];\n'
            '}\n'
        )
        res = run("astack-statechart", "render", str(dot), "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        self.assertEqual(data["states"], 6)
        self.assertEqual(data["transitions"], 5)
        by_name = {v["name"]: v for v in data["violations"]}
        self.assertEqual(by_name["InvA"]["hops"], 1)
        self.assertEqual([s["action"] for s in by_name["InvA"]["steps"]], ["Initial", "Shortcut"])
        self.assertEqual(by_name["InvB"]["hops"], 2)
        self.assertEqual(by_name["InvUnreachable"]["hops"], -1)
        mmd = data["mermaid"]
        self.assertTrue(mmd.startswith("stateDiagram-v2\n"))
        self.assertIn("[*] --> s0", mmd)
        self.assertIn("[VIOLATION: InvA]", mmd)
        self.assertIn("classDef violation", mmd)

    def test_render_with_tlc_trace_parses_invariant_deadlock_and_temporal_cycle(self):
        dot = self.dir / "empty.dot"
        dot.write_text("digraph G {}\n")
        trace = self.dir / "tlc.out"
        trace.write_text(
            "Model checking completed.\n"
            "Error: Invariant Bounded is violated.\n"
            "Error: The behavior up to this point is:\n"
            "State 1: <Initial predicate>\n"
            "/\\ x = 0\n"
            "State 2: <Step>\n"
            "/\\ x = 1\n"
            "State 3: <Step>\n"
            "/\\ x = 2\n"
            "State 4: <Step>\n"
            "/\\ x = 3\n"
            "Error: Invariant Bounded is violated.\n"
            "Error: The behavior up to this point is:\n"
            "State 1: <Initial predicate>\n"
            "/\\ x = 0\n"
            "State 2: <Jump>\n"
            "/\\ x = 3\n"
            "Error: Deadlock reached.\n"
            "Error: The behavior up to this point is:\n"
            "State 1: <Initial predicate>\n"
            "/\\ lock = \"free\"\n"
            "State 2: <Acquire>\n"
            "/\\ lock = \"stuck\"\n"
            "Error: Temporal properties were violated.\n"
            "Error: The behavior up to this point is:\n"
            "State 1: <Initial predicate>\n"
            "/\\ phase = \"wait\"\n"
            "State 2: <Retry>\n"
            "/\\ phase = \"retry\"\n"
            "Back to state 1: <Loop>\n"
            "128 states generated, 42 distinct states found, 0 states left on queue.\n"
            "The depth of the complete state graph search is 7.\n"
        )
        res = run("astack-statechart", "render", str(dot), "--trace", str(trace), "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        by_key = {(v["kind"], v["name"]): v for v in data["violations"]}
        self.assertEqual(by_key[("invariant", "Bounded")]["hops"], 1)
        self.assertEqual(by_key[("deadlock", "Deadlock")]["hops"], 1)
        self.assertEqual(by_key[("temporal", "TemporalProperty")]["cycle_back_to"], 1)
        self.assertIn("cycle", data["mermaid"])

    def test_max_states_always_preserves_initial_and_shortest_failure_path(self):
        lines = ["digraph Big {", '  n0 [label="init", style=filled];']
        for i in range(1, 21):
            lines.append(f'  decoy_{i} [label="decoy {i}"];')
            lines.append(f'  n0 -> decoy_{i} [label="branch_{i}"];')
        lines.append('  p1 [label="step 1"];')
        lines.append('  p2 [label="step 2"];')
        lines.append('  p3 [label="step 3"];')
        lines.append('  bad [label="broken state", color=red, invariant="Safety"];')
        lines.append('  n0 -> p1 [label="e1"];')
        lines.append('  p1 -> p2 [label="e2"];')
        lines.append('  p2 -> p3 [label="e3"];')
        lines.append('  p3 -> bad [label="e4"];')
        lines.append("}")
        dot = self.dir / "big.dot"
        dot.write_text("\n".join(lines) + "\n")
        res = run("astack-statechart", "render", str(dot), "--max-states", "6", "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        self.assertEqual(data["states"], 25)
        self.assertEqual(data["omitted_states"], 19)
        mmd = data["mermaid"]
        for must_have in ("init", "step 1", "step 2", "step 3", "broken state [VIOLATION: Safety]", "19 additional states omitted"):
            self.assertIn(must_have, mmd)

    def test_property_based_adversarial_names_and_bfs_minimality(self):
        adversarial = [
            "__proto__",
            "constructor",
            "prototype",
            "toString",
            "hasOwnProperty",
            "valueOf",
            "end",
            "state",
            "note",
            "classDef",
            "node",
            "edge",
            "digraph",
            "[*]",
            "-->",
            "a --> b",
            'quote"inside',
            "line1\nline2",
            "comment%%here",
            "trailing\\",
            "a:b:c",
            "/\\ x = 0\n/\\ y = 1",
            "",
        ]
        rng = random.Random(20261124)
        state_decl_re = re.compile(r'^    state "([^"]*)" as (s\d+)$')
        edge_re = re.compile(r"^    (\[\*\]|s\d+) --> (s\d+)(?:: .*)?$")

        for trial in range(30):
            n_nodes = rng.randint(4, 14)
            # Always include literal __proto__, constructor, [*], and end with strictly unique node IDs
            pinned = ["__proto__", "constructor", "[*]", "end"]
            rest = [name for name in adversarial if name not in pinned]
            rng.shuffle(rest)
            node_ids = list(pinned) + rest[: n_nodes - len(pinned)]
            self.assertEqual(len(set(node_ids)), n_nodes)

            initial = [node_ids[0]]
            violating = {}
            for idx in rng.sample(range(1, n_nodes), k=rng.randint(1, min(3, n_nodes - 1))):
                inv_name = f"Inv_{adversarial[(idx + trial) % len(adversarial)]}_{idx}"
                violating[node_ids[idx]] = inv_name

            edges = []
            dot_lines = ["digraph Prop {"]
            for nid in node_ids:
                lbl = rng.choice(adversarial)
                attrs = [f'label="{_dot_escape(lbl)}"']
                if nid in initial:
                    attrs.append("style=filled")
                if nid in violating:
                    attrs.append('color=red')
                    attrs.append(f'invariant="{_dot_escape(violating[nid])}"')
                dot_lines.append(f'  "{_dot_escape(nid)}" [{", ".join(attrs)}];')

            for _ in range(rng.randint(n_nodes, n_nodes * 2)):
                src = rng.choice(node_ids)
                dst = rng.choice(node_ids)
                elbl = rng.choice(adversarial)
                edges.append((src, dst))
                dot_lines.append(f'  "{_dot_escape(src)}" -> "{_dot_escape(dst)}" [label="{_dot_escape(elbl)}"];')
            dot_lines.append("}")

            dot_path = self.dir / f"prop_{trial}.dot"
            dot_path.write_text("\n".join(dot_lines) + "\n")
            res = run("astack-statechart", "render", str(dot_path), "--json")
            self.assertEqual(res.returncode, 0, f"trial {trial}: {res.stderr}")
            data = json.loads(res.stdout)
            self.assertEqual(data["states"], n_nodes, f"trial {trial}")

            # Verify every violation's hop count against the independent BFS oracle
            by_inv = {v["name"]: v["hops"] for v in data["violations"]}
            for bad_id, inv_name in violating.items():
                expected_hops = _independent_min_hops(initial, edges, bad_id)
                self.assertEqual(by_inv[inv_name], expected_hops, f"trial {trial} {inv_name}")

            # Verify Mermaid output syntax safety against all adversarial names
            mmd_lines = data["mermaid"].splitlines()
            self.assertEqual(mmd_lines[0], "stateDiagram-v2")
            declared = set()
            for line in mmd_lines[1:]:
                if line.startswith("    classDef ") or line.startswith("    class ") or line.startswith("    %% "):
                    continue
                if m := state_decl_re.match(line):
                    label_body, sid = m.group(1), m.group(2)
                    self.assertNotIn("%%", label_body, f"trial {trial}: comment leaked in {line!r}")
                    self.assertNotIn("-->", label_body, f"trial {trial}: arrow leaked in {line!r}")
                    self.assertNotIn("[*]", label_body, f"trial {trial}: [*] leaked in {line!r}")
                    self.assertFalse(label_body.endswith("\\"), f"trial {trial}: trailing backslash in {line!r}")
                    declared.add(sid)
                elif m := edge_re.match(line):
                    src_id, dst_id = m.group(1), m.group(2)
                    if src_id != "[*]":
                        self.assertIn(src_id, declared, f"trial {trial}: undeclared {src_id}")
                    self.assertIn(dst_id, declared, f"trial {trial}: undeclared {dst_id}")
                else:
                    self.fail(f"trial {trial}: unexpected Mermaid line {line!r}")
            self.assertEqual(len(declared), n_nodes, f"trial {trial}")

    def test_check_invokes_tlc_and_returns_expected_exit_codes(self):
        # Missing model -> exit 2
        missing = run("astack-statechart", "check", str(self.dir / "missing.tla"))
        self.assertEqual(missing.returncode, 2)

        model = self.dir / "Mini.tla"
        model.write_text("---- MODULE Mini ----\n====\n")

        # Missing TLC -> exit 2
        env_no_tlc = {"HOME": str(self.dir), "PATH": "/usr/bin:/bin"}
        no_tlc = subprocess.run(
            [sys.executable, str(BIN / "astack-statechart"), "check", str(model), "--jar", str(self.dir / "nope.jar")],
            capture_output=True, text=True, env=env_no_tlc,
        )
        self.assertEqual(no_tlc.returncode, 2)

        # Fake TLC stub (clean pass -> exit 0, writes DOT, verifies -tool and -dump dot,actionlabels)
        args_log = self.dir / "tlc_args.txt"
        tlc_ok = self.dir / "fake-tlc-ok"
        tlc_ok.write_text(
            "#!/bin/sh\n"
            f'printf "%s\\n" "$@" > "{args_log}"\n'
            'dot_file=""\n'
            'prev=""\n'
            'for a in "$@"; do\n'
            '  if [ "$prev" = "dot,actionlabels" ] || [ "$prev" = "dot" ]; then dot_file="$a"; fi\n'
            '  prev="$a"\n'
            'done\n'
            'printf \'strict digraph DiskGraph { -1 [label="x = 0", style = filled]; 2 [label="x = 1"]; -1 -> 2 [label="Inc", color="black"]; }\\n\' > "$dot_file"\n'
            "printf '%s\\n' '@!@!@STARTMSG 2199:0 @!@!@' '2 states generated, 2 distinct states found, 0 states left on queue.' '@!@!@ENDMSG 2199 @!@!@'\n"
            "printf '%s\\n' '@!@!@STARTMSG 2194:0 @!@!@' 'The depth of the complete state graph search is 1.' '@!@!@ENDMSG 2194 @!@!@'\n"
            'exit 0\n'
        )
        tlc_ok.chmod(0o755)
        out_mmd = self.dir / "out.mmd"
        ok = run("astack-statechart", "check", str(model), "--tlc", str(tlc_ok), "--mermaid", str(out_mmd), "--json")
        self.assertEqual(ok.returncode, 0, ok.stderr)
        passed_args = args_log.read_text().splitlines()
        self.assertIn("-tool", passed_args)
        self.assertIn("dot,actionlabels", passed_args)
        self.assertIn("-continue", passed_args)
        self.assertTrue(out_mmd.is_file())
        ok_data = json.loads(ok.stdout)
        self.assertEqual(ok_data["distinct_states"], 2)
        self.assertEqual(ok_data["parser_mode"], "tool")
        self.assertIn("Inc", ok_data["mermaid"])

        # --stop-on-first omits -continue
        ok2 = run("astack-statechart", "check", str(model), "--tlc", str(tlc_ok), "--stop-on-first", "--json")
        self.assertEqual(ok2.returncode, 0, ok2.stderr)
        self.assertNotIn("-continue", args_log.read_text().splitlines())

        # Fake TLC stub with -tool violation -> exit 1
        tlc_fail = self.dir / "fake-tlc-fail"
        tlc_fail.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' '@!@!@STARTMSG 2110:1 @!@!@' 'Invariant NoOverflow is violated.' '@!@!@ENDMSG 2110 @!@!@'\n"
            "printf '%s\\n' '@!@!@STARTMSG 2217:4 @!@!@' '1: <Initial predicate>' '/\\ x = 0' '@!@!@ENDMSG 2217 @!@!@'\n"
            "printf '%s\\n' '@!@!@STARTMSG 2217:4 @!@!@' '2: <Inc line 4, col 5 to line 4, col 12 of module Mini>' '/\\ x = 1' '@!@!@ENDMSG 2217 @!@!@'\n"
            "exit 12\n"
        )
        tlc_fail.chmod(0o755)
        viol = run("astack-statechart", "check", str(model), "--tlc", str(tlc_fail), "--json")
        self.assertEqual(viol.returncode, 1, viol.stderr)
        vdata = json.loads(viol.stdout)
        self.assertEqual(vdata["violations"][0]["name"], "NoOverflow")
        self.assertEqual(vdata["violations"][0]["hops"], 1)
        self.assertEqual(vdata["violations"][0]["steps"][1]["action"], "Inc")

        # PROBE 1A: TLC writes a DOT graph then exits 12 with an unrecognized error -> MUST exit 1, NEVER false-pass!
        tlc_unrec_12 = self.dir / "fake-tlc-unrec-12"
        tlc_unrec_12.write_text(
            "#!/bin/sh\n"
            'dot_file=""\n'
            'prev=""\n'
            'for a in "$@"; do\n'
            '  if [ "$prev" = "dot,actionlabels" ] || [ "$prev" = "dot" ]; then dot_file="$a"; fi\n'
            '  prev="$a"\n'
            'done\n'
            'printf \'digraph G { 1 [label="x = 0", style=filled]; 2 [label="x = 1"]; 1 -> 2 [label="Step"]; }\\n\' > "$dot_file"\n'
            "printf '%s\\n' 'Error: Assertion failed in Check.'\n"
            "exit 12\n"
        )
        tlc_unrec_12.chmod(0o755)
        res12 = run("astack-statechart", "check", str(model), "--tlc", str(tlc_unrec_12))
        self.assertEqual(res12.returncode, 1, res12.stdout + res12.stderr)
        self.assertNotIn("All checked invariants held", res12.stdout)

        # PROBE 1B: TLC writes a partial DOT graph then crashes with exit 255 -> MUST exit 2, NEVER exit 0!
        tlc_crash_255 = self.dir / "fake-tlc-crash-255"
        tlc_crash_255.write_text(
            "#!/bin/sh\n"
            'dot_file=""\n'
            'prev=""\n'
            'for a in "$@"; do\n'
            '  if [ "$prev" = "dot,actionlabels" ] || [ "$prev" = "dot" ]; then dot_file="$a"; fi\n'
            '  prev="$a"\n'
            'done\n'
            'printf \'digraph G { 1 [label="x = 0", style=filled]; }\\n\' > "$dot_file"\n'
            "printf '%s\\n' 'Exception in thread main: java.lang.OutOfMemoryError' >&2\n"
            "exit 255\n"
        )
        tlc_crash_255.chmod(0o755)
        res255 = run("astack-statechart", "check", str(model), "--tlc", str(tlc_crash_255))
        self.assertEqual(res255.returncode, 2, res255.stdout + res255.stderr)
        self.assertNotIn("All checked invariants held", res255.stdout)

        # Fake TLC stub with parse/tool error -> exit 2
        tlc_err = self.dir / "fake-tlc-err"
        tlc_err.write_text("#!/bin/sh\necho 'Fatal syntax error' >&2\nexit 1\n")
        tlc_err.chmod(0o755)
        err = run("astack-statechart", "check", str(model), "--tlc", str(tlc_err))
        self.assertEqual(err.returncode, 2)

    def test_long_shared_prefix_states_mark_exact_violating_node_and_disambiguate_labels(self):
        # PROBE 2: Two states sharing >120-char queue prefix differing only at the end (y = 0 vs y = 1)
        long_q = "<<" + ", ".join(str(i) for i in range(1, 45)) + ">>"
        healthy_state = f"/\\ q = {long_q}\n/\\ y = 0"
        broken_state = f"/\\ q = {long_q}\n/\\ y = 1"
        self.assertGreater(len(long_q), 150)

        dot = self.dir / "long_prefix.dot"
        dot.write_text(
            "strict digraph DiskGraph {\n"
            f'  -100 [label="{_dot_escape(healthy_state)}", style = filled];\n'
            f'  -200 [label="{_dot_escape(broken_state)}"];\n'
            '  -100 -> -200 [label="Flip", color="black"];\n'
            "}\n"
        )
        trace = self.dir / "long_prefix.tool.out"
        trace.write_text(
            "@!@!@STARTMSG 2110:1 @!@!@\n"
            "Invariant YZero is violated.\n"
            "@!@!@ENDMSG 2110 @!@!@\n"
            "@!@!@STARTMSG 2217:4 @!@!@\n"
            "1: <Initial predicate>\n"
            f"{healthy_state}\n"
            "@!@!@ENDMSG 2217 @!@!@\n"
            "@!@!@STARTMSG 2217:4 @!@!@\n"
            "2: <Flip line 10, col 1 to line 10, col 12 of module Q>\n"
            f"{broken_state}\n"
            "@!@!@ENDMSG 2217 @!@!@\n"
        )
        res = run("astack-statechart", "render", str(dot), "--trace", str(trace), "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        # Violation MUST be marked on -200 (y = 1), NEVER on -100 (y = 0)
        self.assertEqual(data["violating_states"], {"-200": "YZero"})
        self.assertNotIn("-100", data["violating_states"])

        # Rendered Mermaid labels for the two states must be distinct and reveal y = 0 vs y = 1
        state_lines = [ln for ln in data["mermaid"].splitlines() if ln.strip().startswith('state "')]
        self.assertEqual(len(state_lines), 2)
        self.assertNotEqual(state_lines[0], state_lines[1])
        self.assertIn("y = 0", state_lines[0])
        self.assertNotIn("[VIOLATION:", state_lines[0])
        self.assertIn("y = 1", state_lines[1])
        self.assertIn("[VIOLATION: YZero]", state_lines[1])

    def test_recorded_tlc_219_tool_fixtures(self):
        fixtures = Path(__file__).resolve().parent / "fixtures" / "tlc"

        # 1. Deadlock with real TLC 2.19 -tool output + -dump dot,actionlabels
        dl = run(
            "astack-statechart", "render",
            str(fixtures / "counter_deadlock.dot"),
            "--trace", str(fixtures / "counter_deadlock.tool.out"),
            "--json",
        )
        self.assertEqual(dl.returncode, 0, dl.stderr)
        dl_data = json.loads(dl.stdout)
        self.assertEqual(dl_data["states"], 4)
        self.assertEqual(dl_data["transitions"], 3)
        self.assertEqual(dl_data["violating_states"], {"-4900539538744082733": "Deadlock"})
        self.assertEqual(dl_data["violations"][0]["kind"], "deadlock")
        self.assertEqual(dl_data["violations"][0]["hops"], 3)
        self.assertEqual(dl_data["violations"][0]["steps"][1]["action"], "Inc")
        self.assertIn("s0 --> s1: Inc", dl_data["mermaid"])

        # 2. Initial-state invariant violation (EC 2107) with empty DOT
        empty_dot = self.dir / "empty_init.dot"
        empty_dot.write_text("strict digraph DiskGraph { subgraph cluster_graph { color=\"white\"; } }\n")
        init_v = run(
            "astack-statechart", "render",
            str(empty_dot),
            "--trace", str(fixtures / "initial_violation.tool.out"),
            "--json",
        )
        self.assertEqual(init_v.returncode, 0, init_v.stderr)
        init_data = json.loads(init_v.stdout)
        self.assertEqual(init_data["violations"][0]["kind"], "invariant")
        self.assertEqual(init_data["violations"][0]["name"], "NotNine")
        self.assertEqual(init_data["violations"][0]["hops"], 0)
        self.assertIn("x = 9 [VIOLATION: NotNine]", init_data["mermaid"])

        # 3. Temporal loop (EC 2116 + 2122)
        loop_v = run(
            "astack-statechart", "render",
            str(empty_dot),
            "--trace", str(fixtures / "temporal_loop.tool.out"),
            "--json",
        )
        self.assertEqual(loop_v.returncode, 0, loop_v.stderr)
        loop_data = json.loads(loop_v.stdout)
        self.assertEqual(loop_data["violations"][0]["kind"], "temporal")
        self.assertEqual(loop_data["violations"][0]["hops"], 2)
        self.assertEqual(loop_data["violations"][0]["cycle_back_to"], 2)
        self.assertIn("cycle", loop_data["mermaid"])

        # 4. Action property (EC 2112) + stuttering liveness (EC 2218)
        act_v = run(
            "astack-statechart", "render",
            str(empty_dot),
            "--trace", str(fixtures / "action_and_stuttering.tool.out"),
            "--json",
        )
        self.assertEqual(act_v.returncode, 0, act_v.stderr)
        act_data = json.loads(act_v.stdout)
        by_name = {v["name"]: v for v in act_data["violations"]}
        self.assertEqual(by_name["Monotonic"]["kind"], "property")
        self.assertEqual(by_name["Monotonic"]["hops"], 1)
        self.assertEqual(by_name["Monotonic"]["steps"][1]["action"], "Drop")
        self.assertEqual(by_name["TemporalProperty"]["cycle_back_to"], 1)

    @unittest.skipUnless(_has_real_tlc(), "TLC / tla2tools.jar not installed")
    def test_check_against_real_tlc_when_installed(self):
        tla = self.dir / "Counter.tla"
        tla.write_text(
            "---- MODULE Counter ----\n"
            "EXTENDS Naturals\n"
            "VARIABLE x\n"
            "Init == x = 0\n"
            "Next == x < 4 /\\ x' = x + 1\n"
            "Safe == x <= 4\n"
            "Broken == x <= 2\n"
            "====\n"
        )
        cfg_ok = self.dir / "ok.cfg"
        cfg_ok.write_text("INIT Init\nNEXT Next\nINVARIANT Safe\n")
        ok = run("astack-statechart", "check", str(tla), "--cfg", str(cfg_ok), "--json")
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertEqual(json.loads(ok.stdout)["violations"], [])

        cfg_bad = self.dir / "bad.cfg"
        cfg_bad.write_text("INIT Init\nNEXT Next\nINVARIANT Broken\n")
        bad = run("astack-statechart", "check", str(tla), "--cfg", str(cfg_bad), "--json")
        self.assertEqual(bad.returncode, 1, bad.stderr)
        bdata = json.loads(bad.stdout)
        self.assertEqual(bdata["violations"][0]["name"], "Broken")
        self.assertEqual(bdata["violations"][0]["hops"], 3)


class CheckGatesTest(Scratch):
    def setUp(self):
        super().setUp()
        self.origin = self.dir / "origin.git"
        git(self.dir, "init", "-q", "--bare", "-b", "main", str(self.origin))
        self.repo = self.dir / "repo"
        git(self.dir, "clone", "-q", str(self.origin), str(self.repo))
        git(self.repo, "checkout", "-q", "-b", "main")
        (self.repo / "tests").mkdir()
        self.base = commit(
            self.repo,
            "tests/test_app.py",
            "import unittest\nclass T(unittest.TestCase):\n    def test_a(self):\n        self.assertEqual(1 + 1, 2)\n        self.assertEqual(2 + 2, 4)\n",
        )
        git(self.repo, "push", "-q", "origin", "main")

    def test_clean_commit_exits_zero(self):
        sha = commit(self.repo, "app.py", "def add(a, b):\n    return a + b\n")
        res = run("astack-check-gates", sha, "--repo", str(self.repo), "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue(json.loads(res.stdout)["clean"])

    def test_flags_skips_suppressions_weakened_assertions_and_config_edits(self):
        # 1. Test skip + tautological assert + net dropped assertions
        sha_test = commit(
            self.repo,
            "tests/test_app.py",
            "import unittest\nclass T(unittest.TestCase):\n    @unittest.skip('flaky')\n    def test_a(self):\n        assert True\n",
        )
        res_test = run("astack-check-gates", sha_test, "--repo", str(self.repo), "--json")
        self.assertEqual(res_test.returncode, 1)
        cats = {f["category"] for f in json.loads(res_test.stdout)["findings"]}
        self.assertIn("test-skip", cats)
        self.assertIn("weakened-assertion", cats)

        # 2. Lint / typecheck suppressions
        sha_lint = commit(self.repo, "app.py", "x = 1  # noqa: F401\ny = 2  # type: ignore\n")
        res_lint = run("astack-check-gates", sha_lint, "--repo", str(self.repo), "--json")
        self.assertEqual(res_lint.returncode, 1)
        self.assertEqual(len(json.loads(res_lint.stdout)["findings"]), 2)

        # 3. CI / gate config modification
        (self.repo / ".github" / "workflows").mkdir(parents=True)
        sha_ci = commit(self.repo, ".github/workflows/ci.yml", "name: CI\n")
        res_ci = run("astack-check-gates", sha_ci, "--repo", str(self.repo), "--json")
        self.assertEqual(res_ci.returncode, 1)
        self.assertEqual(json.loads(res_ci.stdout)["findings"][0]["category"], "gate-config-edit")

        # 4. verify-merge surfaces GATE SIGNALS and fails under --strict-gates
        git(self.repo, "push", "-q", "origin", "main")
        warn_res = run("astack-verify-merge", sha_test, "--repo", str(self.repo), cache=self.dir / "cache")
        self.assertEqual(warn_res.returncode, 0, warn_res.stdout)
        self.assertIn("GATE SIGNALS", warn_res.stdout)

        strict_res = run("astack-verify-merge", sha_test, "--strict-gates", "--repo", str(self.repo), cache=self.dir / "cache")
        self.assertEqual(strict_res.returncode, 1, strict_res.stdout)
        self.assertTrue(strict_res.stdout.startswith("NOT VERIFIED:"))
        self.assertIn("GATE SIGNALS", strict_res.stdout)

    def test_catches_earlier_lane_commit_deletions_renames_downgrades_tolerances_and_fails_closed(self):
        # Set up a multi-commit lane: commit 1 adds a skip, commit 2 is clean
        lane_base = git(self.repo, "rev-parse", "HEAD")
        commit(
            self.repo,
            "tests/test_multi.py",
            "import unittest\nclass M(unittest.TestCase):\n    @unittest.skip('later')\n    def test_x(self):\n        self.assertEqual(1, 1)\n",
        )
        clean_head = commit(self.repo, "clean.py", "VAL = 42\n")
        git(self.repo, "push", "-q", "origin", "main")

        # Checking full lane range via --base catches commit 1's skip even though clean_head itself is clean
        ranged = run(
            "astack-verify-merge", clean_head, "--base", lane_base, "--strict-gates",
            "--repo", str(self.repo), cache=self.dir / "cache",
        )
        self.assertEqual(ranged.returncode, 1, ranged.stdout)
        self.assertIn("test-skip", ranged.stdout)

        # 1. Assertion downgrade: assertEqual -> assertIsNotNone
        commit(
            self.repo,
            "tests/test_downgrade.py",
            "import unittest\nclass D(unittest.TestCase):\n    def test_v(self):\n        self.assertEqual(1, 1)\n        self.assertAlmostEqual(1.0, 1.0, places=9)\n",
        )
        sha_down = commit(
            self.repo,
            "tests/test_downgrade.py",
            "import unittest\nclass D(unittest.TestCase):\n    def test_v(self):\n        self.assertIsNotNone(1)\n        self.assertAlmostEqual(1.0, 1.0, places=1)\n",
        )
        res_down = run("astack-check-gates", sha_down, "--repo", str(self.repo), "--json")
        self.assertEqual(res_down.returncode, 1, res_down.stdout)
        reasons = [f["reason"] for f in json.loads(res_down.stdout)["findings"]]
        self.assertTrue(any("weaker presence/truthiness" in r for r in reasons), reasons)
        self.assertTrue(any("places 9 -> 1" in r for r in reasons), reasons)

        # 2. Tolerance increase: abs_tol=1e-6 -> abs_tol=0.1
        commit(self.repo, "tests/test_tol.py", "import math\ndef test_c():\n    assert math.isclose(1.0, 1.0, abs_tol=1e-6)\n")
        sha_tol = commit(self.repo, "tests/test_tol.py", "import math\ndef test_c():\n    assert math.isclose(1.0, 1.0, abs_tol=0.1)\n")
        res_tol = run("astack-check-gates", sha_tol, "--repo", str(self.repo), "--json")
        self.assertEqual(res_tol.returncode, 1, res_tol.stdout)
        self.assertTrue(any("abs_tol" in f["reason"] for f in json.loads(res_tol.stdout)["findings"]))

        # 3. Entire test file deleted (+++ /dev/null must NOT drop the file!)
        git(self.repo, "rm", "-q", "tests/test_tol.py")
        git(self.repo, "commit", "-q", "-m", "delete test file")
        sha_del = git(self.repo, "rev-parse", "HEAD")
        res_del = run("astack-check-gates", sha_del, "--repo", str(self.repo), "--json")
        self.assertEqual(res_del.returncode, 1, res_del.stdout)
        self.assertIn("deleted-test-file", {f["category"] for f in json.loads(res_del.stdout)["findings"]})

        # 4. Test function renamed so runner skips it (def test_v -> def _test_v)
        sha_ren = commit(
            self.repo,
            "tests/test_downgrade.py",
            "import unittest\nclass D(unittest.TestCase):\n    def _test_v(self):\n        self.assertIsNotNone(1)\n        self.assertAlmostEqual(1.0, 1.0, places=1)\n",
        )
        res_ren = run("astack-check-gates", sha_ren, "--repo", str(self.repo), "--json")
        self.assertEqual(res_ren.returncode, 1, res_ren.stdout)
        self.assertIn("dropped-test", {f["category"] for f in json.loads(res_ren.stdout)["findings"]})

        # 5. Test file renamed out of test discovery (tests/test_downgrade.py -> helpers/downgrade_notes.py)
        (self.repo / "helpers").mkdir()
        git(self.repo, "mv", "tests/test_downgrade.py", "helpers/downgrade_notes.py")
        git(self.repo, "commit", "-q", "-m", "rename test file away")
        sha_mv = git(self.repo, "rev-parse", "HEAD")
        res_mv = run("astack-check-gates", sha_mv, "--repo", str(self.repo), "--json")
        self.assertEqual(res_mv.returncode, 1, res_mv.stdout)
        self.assertIn("deleted-test-file", {f["category"] for f in json.loads(res_mv.stdout)["findings"]})

        # 6. verify-merge FAILS CLOSED (exit 2, NOT 0) if astack-check-gates errors or is missing!
        isolated_bin = self.dir / "broken-bin"
        isolated_bin.mkdir()
        shutil.copy2(BIN / "astack-verify-merge", isolated_bin / "astack-verify-merge")
        broken_checker = isolated_bin / "astack-check-gates"
        broken_checker.write_text("import sys\nprint('boom', file=sys.stderr)\nsys.exit(2)\n")
        broken_checker.chmod(0o755)
        fail_closed = subprocess.run(
            [sys.executable, str(isolated_bin / "astack-verify-merge"), clean_head, "--strict-gates", "--repo", str(self.repo)],
            capture_output=True, text=True, env={**os.environ, "XDG_CACHE_HOME": str(self.dir / "cache")},
        )
        self.assertEqual(fail_closed.returncode, 2, fail_closed.stdout + fail_closed.stderr)
        self.assertTrue(fail_closed.stdout.startswith("NOT CHECKED:"), fail_closed.stdout)

        # Also fail closed when astack-check-gates is missing entirely
        broken_checker.unlink()
        missing_checker = subprocess.run(
            [sys.executable, str(isolated_bin / "astack-verify-merge"), clean_head, "--strict-gates", "--repo", str(self.repo)],
            capture_output=True, text=True, env={**os.environ, "XDG_CACHE_HOME": str(self.dir / "cache")},
        )
        self.assertEqual(missing_checker.returncode, 2, missing_checker.stdout + missing_checker.stderr)
        self.assertTrue(missing_checker.stdout.startswith("NOT CHECKED:"), missing_checker.stdout)


if __name__ == "__main__":
    unittest.main()
