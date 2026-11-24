"""Behaviour tests for astack's scripts: what a lead or a hook sees when it runs them."""
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import unittest
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

        # Antigravity PostToolUse payload (Path / CommandLine keys)
        path2 = self.log("ended b: MERGED def\n")
        agy_event = {"tool_name": "write_file", "tool_input": {"Path": str(path2)}, "cwd": str(self.dir)}
        self.assertEqual(run("astack-stamp", "--hook", stdin=json.dumps(agy_event)).returncode, 0)
        self.assertRegex(path2.read_text().splitlines()[-1], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z ended b: MERGED def$")

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
        for cli in ("claude", "codex", "agy", "pi", "cursor-agent", "devin"):
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
            self.assertEqual(data["harnesses"]["pi"]["provider"], "multi")
            self.assertEqual(data["harnesses"]["cursor"]["path"], str(bin_home / "cursor-agent"))
            self.assertEqual(data["harnesses"]["devin"]["provider"], "devin")

    def test_link_bin_installs_scripts_idempotently_and_supports_copy(self):
        bin_dir = self.dir / "user-bin"
        first = run("astack-tools", "link-bin", "--bin-dir", str(bin_dir))
        self.assertEqual(first.returncode, 0, first.stderr)
        for name in ("astack-tools", "astack-dispatch", "astack-status", "astack-decisions", "astack-verify-merge", "astack-check-gates", "astack-review-ledger", "astack-statechart", "astack-stamp"):
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

    def test_pytest_idioms_backmerge_isolation_and_cross_file_test_moves(self):
        # 1. Pytest bare truthiness downgrade (assert result == 6 -> assert result) + pytest.approx rel=/abs= loosening
        commit(
            self.repo,
            "tests/test_pytest_style.py",
            "import pytest\ndef test_calc():\n    result = calc(3)\n    assert result == 6\n    assert result == pytest.approx(6.0, rel=1e-9, abs=1e-9)\n",
        )
        sha_pt = commit(
            self.repo,
            "tests/test_pytest_style.py",
            "import pytest\ndef test_calc():\n    result = calc(3)\n    assert result\n    assert result == pytest.approx(6.0, rel=0.5, abs=0.2)\n",
        )
        res_pt = run("astack-check-gates", sha_pt, "--repo", str(self.repo), "--json")
        self.assertEqual(res_pt.returncode, 1, res_pt.stdout)
        pt_reasons = [f["reason"] for f in json.loads(res_pt.stdout)["findings"]]
        self.assertTrue(any("weaker presence/truthiness" in r for r in pt_reasons), pt_reasons)
        self.assertTrue(any("rel " in r or "abs " in r for r in pt_reasons), pt_reasons)

        # 2. Moving a real test between files (refactor) produces ZERO false flags
        move_base = commit(
            self.repo,
            "tests/test_src.py",
            "def test_one():\n    assert compute(1) == 2\n    assert compute(2) == 4\ndef test_two():\n    assert compute(3) == 6\n",
        )
        (self.repo / "tests" / "test_src.py").write_text("def test_one():\n    assert compute(1) == 2\n    assert compute(2) == 4\n")
        (self.repo / "tests" / "test_dst.py").write_text("def test_two():\n    assert compute(3) == 6\n")
        git(self.repo, "add", "tests/test_src.py", "tests/test_dst.py")
        git(self.repo, "commit", "-q", "-m", "move test_two to test_dst")
        move_head = git(self.repo, "rev-parse", "HEAD")
        res_move = run("astack-check-gates", f"{move_base}..{move_head}", "--repo", str(self.repo), "--json")
        self.assertEqual(res_move.returncode, 0, res_move.stdout)
        self.assertTrue(json.loads(res_move.stdout)["clean"])

        # 3. Test swaps (deleting a real test and adding a trivial one elsewhere) MUST be caught!
        # 3a. Constant tautology swap (assert 1 == 1)
        swap_base = git(self.repo, "rev-parse", "HEAD")
        (self.repo / "tests" / "test_dst.py").write_text("# removed\n")
        (self.repo / "tests" / "test_fake1.py").write_text("def test_trivial():\n    assert 1 == 1\n")
        git(self.repo, "add", "tests/test_dst.py", "tests/test_fake1.py")
        git(self.repo, "commit", "-q", "-m", "swap real test for constant tautology")
        res_swap1 = run("astack-check-gates", f"{swap_base}..HEAD", "--repo", str(self.repo), "--json")
        self.assertEqual(res_swap1.returncode, 1, res_swap1.stdout)
        self.assertIn("weakened-assertion", {f["category"] for f in json.loads(res_swap1.stdout)["findings"]})

        # 3b. Cross-file strong->weak swap (assert compute(2) == 4 -> assert res in another file)
        swap2_base = git(self.repo, "rev-parse", "HEAD")
        (self.repo / "tests" / "test_src.py").write_text("def test_one():\n    assert compute(1) == 2\n")
        (self.repo / "tests" / "test_fake2.py").write_text("def test_weak():\n    res = compute(2)\n    assert res\n")
        git(self.repo, "add", "tests/test_src.py", "tests/test_fake2.py")
        git(self.repo, "commit", "-q", "-m", "swap strong assert for bare truthiness elsewhere")
        res_swap2 = run("astack-check-gates", f"{swap2_base}..HEAD", "--repo", str(self.repo), "--json")
        self.assertEqual(res_swap2.returncode, 1, res_swap2.stdout)
        self.assertTrue(any("cross-diff test swap" in f["reason"] for f in json.loads(res_swap2.stdout)["findings"]), res_swap2.stdout)

        # 3c. Assertion-free stub test swap (`def test_stub(): pass`)
        swap3_base = git(self.repo, "rev-parse", "HEAD")
        (self.repo / "tests" / "test_fake3.py").write_text("def test_stub():\n    pass\n")
        git(self.repo, "add", "tests/test_fake3.py")
        git(self.repo, "commit", "-q", "-m", "add assertion-free test")
        res_swap3 = run("astack-check-gates", f"{swap3_base}..HEAD", "--repo", str(self.repo), "--json")
        self.assertEqual(res_swap3.returncode, 1, res_swap3.stdout)
        self.assertTrue(any("without any assertion" in f["reason"] for f in json.loads(res_swap3.stdout)["findings"]), res_swap3.stdout)

        # 4. Merge spoofing MUST fail closed (astack-verify-merge NEVER trusts commit messages!):
        git(self.repo, "push", "-q", "origin", "main")
        fork_base = git(self.repo, "rev-parse", "HEAD")

        # Attack A: gamed lane merged into clean main WITH forged commit message "Merge branch 'main'"
        git(self.repo, "checkout", "-q", "-b", "lane/spoof-a", fork_base)
        commit(
            self.repo,
            "tests/test_spoof_a.py",
            "import unittest\nclass SA(unittest.TestCase):\n    @unittest.skip('gamed')\n    def test_sa(self):\n        self.assertEqual(calc(1), 2)\n",
        )
        git(self.repo, "checkout", "-q", "main")
        main_before_a = commit(self.repo, "other_a.py", "A = 1\n")
        git(self.repo, "merge", "-q", "--no-ff", "-m", "Merge branch 'main'", "lane/spoof-a")
        spoof_a = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "push", "-q", "origin", "main")

        res_spoof_a_bare = run("astack-verify-merge", spoof_a, "--strict-gates", "--repo", str(self.repo), cache=self.dir / "cache")
        self.assertEqual(res_spoof_a_bare.returncode, 1, res_spoof_a_bare.stdout)
        self.assertIn("test-skip", res_spoof_a_bare.stdout)

        res_spoof_a_base = run("astack-verify-merge", spoof_a, "--base", main_before_a, "--strict-gates", "--repo", str(self.repo), cache=self.dir / "cache")
        self.assertEqual(res_spoof_a_base.returncode, 1, res_spoof_a_base.stdout)
        self.assertIn("test-skip", res_spoof_a_base.stdout)

        # Attack B: gamed lane back-merges clean main WITH custom message "Sync upstream" (no "main")
        fork_b = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "checkout", "-q", "-b", "lane/spoof-b", fork_b)
        commit(
            self.repo,
            "tests/test_spoof_b.py",
            "import unittest\nclass SB(unittest.TestCase):\n    @unittest.skip('gamed')\n    def test_sb(self):\n        self.assertEqual(calc(2), 4)\n",
        )
        git(self.repo, "checkout", "-q", "main")
        main_before_b = commit(self.repo, "other_b.py", "B = 2\n")
        git(self.repo, "push", "-q", "origin", "main")
        git(self.repo, "checkout", "-q", "lane/spoof-b")
        git(self.repo, "merge", "-q", "-m", "Sync upstream", "origin/main")
        spoof_b = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "checkout", "-q", "main")
        git(self.repo, "merge", "-q", "--ff-only", "lane/spoof-b")
        git(self.repo, "push", "-q", "origin", "main")

        res_spoof_b_bare = run("astack-verify-merge", spoof_b, "--strict-gates", "--repo", str(self.repo), cache=self.dir / "cache")
        self.assertEqual(res_spoof_b_bare.returncode, 1, res_spoof_b_bare.stdout)
        self.assertIn("test-skip", res_spoof_b_bare.stdout)

        res_spoof_b_base = run("astack-verify-merge", spoof_b, "--base", main_before_b, "--strict-gates", "--repo", str(self.repo), cache=self.dir / "cache")
        self.assertEqual(res_spoof_b_base.returncode, 1, res_spoof_b_base.stdout)
        self.assertIn("test-skip", res_spoof_b_base.stdout)

        # 5. Clean Lane-1 back-merges main containing Lane-2's countersigned skip:
        #    verifying with --base <last-verified-main (lane2_sha)> isolates Lane-1 strictly and passes CLEAN!
        fork_c = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "checkout", "-q", "-b", "lane/clean-c", fork_c)
        commit(self.repo, "lane1.py", "def ok():\n    return True\n")
        git(self.repo, "checkout", "-q", "main")
        lane2_sha = commit(
            self.repo,
            "tests/test_lane2.py",
            "import unittest\nclass L2(unittest.TestCase):\n    @unittest.skip('countersigned')\n    def test_l2(self):\n        self.assertEqual(calc(3), 6)\n",
        )
        git(self.repo, "push", "-q", "origin", "main")
        git(self.repo, "checkout", "-q", "lane/clean-c")
        git(self.repo, "merge", "-q", "--no-edit", "origin/main")
        lane1_merge = git(self.repo, "rev-parse", "HEAD")
        git(self.repo, "checkout", "-q", "main")
        git(self.repo, "merge", "-q", "--ff-only", "lane/clean-c")
        git(self.repo, "push", "-q", "origin", "main")

        # Strict tree diff against last verified target commit (lane2_sha) is 100% clean
        v_strict = run(
            "astack-verify-merge", lane1_merge, "--base", lane2_sha, "--strict-gates",
            "--repo", str(self.repo), cache=self.dir / "cache",
        )
        self.assertEqual(v_strict.returncode, 0, v_strict.stdout + v_strict.stderr)
        self.assertTrue(v_strict.stdout.startswith("VERIFIED:"), v_strict.stdout)
        self.assertIn("lane1.py", v_strict.stdout)
        self.assertNotIn("test_lane2.py", v_strict.stdout)

        # Without --base, merge commit audits BOTH parents and surfaces parent 1's skip with --base guidance
        v_no_base = run(
            "astack-verify-merge", lane1_merge, "--strict-gates",
            "--repo", str(self.repo), cache=self.dir / "cache",
        )
        self.assertEqual(v_no_base.returncode, 1, v_no_base.stdout)
        self.assertIn("pass --base <last-verified-target-sha>", v_no_base.stdout)

    def test_ordinary_new_tests_pass_clean_while_swaps_and_stubs_fail(self):
        # 1. Ordinary new tests across pytest.raises, np.testing.assert_allclose, Go testify require.Equal,
        #    Rust #[test] / #[should_panic], and custom helper calls (with nothing removed) MUST pass clean!
        base = git(self.repo, "rev-parse", "HEAD")
        commit(
            self.repo,
            "tests/test_raises_and_np.py",
            "import numpy as np\nimport pytest\n\n"
            "def test_bad_input():\n"
            "    with pytest.raises(ValueError):\n"
            "        parse('bad')\n\n"
            "def test_numerics():\n"
            "    np.testing.assert_allclose(compute_vec(), [1.0, 2.0], rtol=1e-6)\n\n"
            "def test_custom_helper():\n"
            "    verify_roundtrip({'k': 'v'})\n",
        )
        commit(
            self.repo,
            "math_test.go",
            "package mathx\nimport (\n    \"testing\"\n    \"github.com/stretchr/testify/require\"\n)\n"
            "func TestAdd(t *testing.T) {\n"
            "    require.Equal(t, 4, Add(2, 2))\n"
            "}\n"
            "func TestOneLine(t *testing.T) { require.NoError(t, Run()) }\n",
        )
        commit(
            self.repo,
            "tests/lib_test.rs",
            "#[test]\n"
            "fn test_sum() {\n"
            "    assert_eq!(add(2, 2), 4);\n"
            "}\n"
            "#[test]\n"
            "#[should_panic(expected = \"boom\")]\n"
            "fn test_panics() {\n"
            "    explode();\n"
            "}\n",
        )
        clean_res = run("astack-check-gates", f"{base}..HEAD", "--repo", str(self.repo), "--json")
        self.assertEqual(clean_res.returncode, 0, clean_res.stdout + clean_res.stderr)
        self.assertTrue(json.loads(clean_res.stdout)["clean"], clean_res.stdout)

        # 2. Swapping a real assertion for `assert isinstance(...)` MUST be flagged
        commit(self.repo, "tests/test_swap_isinstance.py", "def test_val():\n    res = calc(3)\n    assert res == 6\n")
        sha_inst = commit(self.repo, "tests/test_swap_isinstance.py", "def test_val():\n    res = calc(3)\n    assert isinstance(res, int)\n")
        res_inst = run("astack-check-gates", sha_inst, "--repo", str(self.repo), "--json")
        self.assertEqual(res_inst.returncode, 1, res_inst.stdout)
        self.assertIn("weakened-assertion", {f["category"] for f in json.loads(res_inst.stdout)["findings"]})

        # 3. Go testify tautology `require.Equal(t, 1, 1)` MUST be flagged
        sha_go_taut = commit(
            self.repo,
            "taut_test.go",
            "package mathx\nfunc TestFake(t *testing.T) {\n    require.Equal(t, 1, 1)\n}\n",
        )
        res_go_taut = run("astack-check-gates", sha_go_taut, "--repo", str(self.repo), "--json")
        self.assertEqual(res_go_taut.returncode, 1, res_go_taut.stdout)

        # 4. Empty Go stub test `func TestStub(t *testing.T) {}` MUST be flagged even with nothing removed
        sha_go_stub = commit(self.repo, "stub_test.go", "package mathx\nfunc TestStub(t *testing.T) {}\n")
        res_go_stub = run("astack-check-gates", sha_go_stub, "--repo", str(self.repo), "--json")
        self.assertEqual(res_go_stub.returncode, 1, res_go_stub.stdout)
        self.assertTrue(any("empty/stub" in f["reason"] for f in json.loads(res_go_stub.stdout)["findings"]), res_go_stub.stdout)

        # 5. Swapping a real test for an assertion-free call (`def test_fake(): calc(3)`) MUST be flagged
        swap_base = commit(self.repo, "tests/test_real_swap.py", "def test_real():\n    assert calc(3) == 6\n")
        sha_fake_swap = commit(self.repo, "tests/test_real_swap.py", "def test_fake():\n    calc(3)\n")
        res_fake_swap = run("astack-check-gates", f"{swap_base}..{sha_fake_swap}", "--repo", str(self.repo), "--json")
        self.assertEqual(res_fake_swap.returncode, 1, res_fake_swap.stdout)
        self.assertIn("weakened-assertion", {f["category"] for f in json.loads(res_fake_swap.stdout)["findings"]})


if __name__ == "__main__":
    unittest.main()
