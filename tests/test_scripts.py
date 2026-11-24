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
        for name in ("astack-tools", "astack-status", "astack-decisions", "astack-verify-merge", "astack-stamp"):
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


if __name__ == "__main__":
    unittest.main()
