"""Behaviour tests for astack's scripts: what a lead or a hook sees when it runs them."""
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent / "bin"
SKILLS = BIN.parent / "skills"
MARKER = "<!-- astack lane log -->"


def run(script, *args, stdin=None, cwd=None, cache=None, extra_env=None):
    env = None
    if cache or extra_env:
        env = dict(os.environ)
        if cache:
            env["XDG_CACHE_HOME"] = str(cache)
        if extra_env:
            env.update(extra_env)
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

    def test_add_appends_a_stamped_line_without_a_hook(self):
        path = self.log("2026-11-23T14:02Z started a on x (1)\n")
        added = run("astack-stamp", "--add", str(path), "steer", "a:", "stop  the A/B")
        self.assertEqual(added.returncode, 0, added.stderr)
        lines = path.read_text().splitlines()
        self.assertRegex(lines[-1], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z steer a: stop the A/B$")
        self.assertEqual(lines[-2], "2026-11-23T14:02Z started a on x (1)")
        other = self.dir / "notes.md"
        other.write_text("plain notes\n")
        refused = run("astack-stamp", "--add", str(other), "x")
        self.assertEqual(refused.returncode, 1)
        self.assertEqual(other.read_text(), "plain notes\n")

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

    def status(self, *args):
        return run(
            "astack-status",
            *args,
            cache=self.dir / "empty-cache",
            extra_env={"ASTACK_DISPATCH_STATE_DIR": str(self.dir / "empty-dispatches")},
        )

    def write_log(self, lines):
        path = self.dir / "prog" / "LANES.md"
        path.parent.mkdir()
        path.write_text(f"{MARKER}\n# prog lane log\n\nRepository: {self.repo}\n\n## Log\n\n" + "\n".join(lines) + "\n")
        return path

    def test_says_when_log_lines_have_no_stamp_instead_of_reporting_no_agents(self):
        path = self.write_log([f"started search-1 on search (a1) | branch lane/search | wind-down {stamp_at(5)} | ends {stamp_at(10)} | deliverable: d | done when: e"])
        result = self.status(str(path))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1 log line(s) have no UTC stamp", result.stdout)
        self.assertIn("astack-stamp", result.stdout)
        line = self.status(str(path), "--line")
        self.assertIn("1 log lines have no stamp", line.stdout)
        # Stamped, it counts.
        self.assertEqual(run("astack-stamp", str(path)).returncode, 0)
        stamped = self.status(str(path))
        self.assertNotIn("no UTC stamp", stamped.stdout)
        self.assertIn("search-1", stamped.stdout)

    def test_shows_running_workers_with_their_clocks_and_commits(self):
        path = self.write_log([
            f"{stamp_at(-50)} started search-1 on search (a1) | branch lane/search | wind-down {stamp_at(5)} | ends {stamp_at(10)} | deliverable: d | done when: e",
            f"{stamp_at(-70)} started ingest-1 on ingest (b1) | branch lane/ingest | wind-down {stamp_at(-15)} | ends {stamp_at(-10)} | deliverable: d | done when: e",
            f"{stamp_at(-90)} started old-1 on old (c1) | branch lane/old | wind-down {stamp_at(-35)} | ends {stamp_at(-30)} | deliverable: d | done when: e",
            f"{stamp_at(-31)} ended old-1: MERGED 123 (verified)",
            f"{stamp_at(-30)} closed old: done",
        ])
        result = self.status(str(path))
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
        out = self.status(str(path)).stdout
        self.assertIn("Ship the faster parser now?", out)
        self.assertNotIn("Keep the old export format?", out)

    def test_reads_a_successor_line_from_the_template_format(self):
        path = self.write_log([
            f"{stamp_at(-2)} started search-2 on search (a2) | successor of search-1 | branch lane/search | wind-down {stamp_at(53)} | ends {stamp_at(58)} | deliverable: d | done when: e",
        ])
        out = self.status(str(path)).stdout
        self.assertIn("search-2 on search (agent a2, successor of search-1)", out)

    def test_one_line_summary(self):
        path = self.write_log([
            f"{stamp_at(-50)} started a-1 on a (x) | branch lane/search | wind-down {stamp_at(5)} | ends {stamp_at(10)} | deliverable: d | done when: e",
            f"{stamp_at(-70)} started b-1 on b (y) | branch lane/b | wind-down {stamp_at(-15)} | ends {stamp_at(-10)} | deliverable: d | done when: e",
            f"{stamp_at(-1)} asked: \"Which?\"",
        ])
        line = self.status(str(path), "--line").stdout.strip()
        self.assertRegex(line, r"^astack prog: 2 running · next end \d\d:\d\dZ \(\d+m\) · 1 past limit · 1 waiting on you$")

    def test_tracks_reviewer_and_researcher_timers_alongside_workers(self):
        path = self.write_log([
            f"{stamp_at(-40)} started w-1 on api (a1) | branch lane/search | wind-down {stamp_at(15)} | ends {stamp_at(20)} | deliverable: d | done when: e",
            f"{stamp_at(-35)} started rev-1 on concurrency (r1) | role reviewer | model openai/gpt-6.2-astra | wind-down {stamp_at(-10)} | ends {stamp_at(-5)} | scope: repo/src/inventory.py",
            f"{stamp_at(-20)} started res-1 on auth-history (q1) | role researcher | wind-down {stamp_at(5)} | ends {stamp_at(10)} | question: why was token tag added?",
            f"{stamp_at(-50)} started rev-done on pricing (r0) | role reviewer | model anthropic/sonnet | wind-down {stamp_at(-25)} | ends {stamp_at(-20)} | scope: repo/src/pricing.py",
            f"{stamp_at(-25)} ended rev-done: CLEAR; blocking=0 minor=1 dropped=0",
        ])
        result = self.status(str(path))
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout
        self.assertIn("Running workers", out)
        self.assertIn("Running reviewers", out)
        self.assertIn("rev-1 on concurrency (agent r1, model openai/gpt-6.2-astra)", out)
        self.assertIn("scope: repo/src/inventory.py", out)
        self.assertRegex(out, r"ends \d\d:\d\dZ \(PAST by \d+m\)")
        self.assertIn("Running researchers", out)
        self.assertIn("res-1 on auth-history (agent q1)", out)
        self.assertIn("question: why was token tag added?", out)
        self.assertNotIn("rev-done", out)
        # Non-worker roles must NOT pollute Lanes counts
        self.assertIn("api: open, 1 worker", out)
        self.assertNotIn("concurrency: open", out)
        self.assertNotIn("auth-history: open", out)
        line = self.status(str(path), "--line").stdout.strip()
        self.assertRegex(line, r"^astack prog: 3 running \(1w, 1r, 1res\) · next end \d\d:\d\dZ \(\d+m\) · 1 past limit$")


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
        for name in (
            "astack-tools", "astack-dispatch", "astack-status", "astack-decisions",
            "astack-verify-merge", "astack-check-gates", "astack-review-ledger",
            "astack-statechart", "astack-stamp",
            "astack-watch-pr", "astack-watch-github", "astack-watch-gitlab", "astack-watch-bitbucket",
            "astack-watch-tickets",
            "astack-release", "astack-go-mode",
        ):
            launcher = bin_dir / name
            self.assertTrue(launcher.is_file() and not launcher.is_symlink(), f"missing launcher {launcher}")
            self.assertTrue(os.access(launcher, os.X_OK), f"{launcher} isn't executable")

        # Re-running is idempotent
        second = run("astack-tools", "link-bin", "--bin-dir", str(bin_dir))
        self.assertEqual(second.returncode, 0, second.stderr)

        # --copy mode writes executable copies AND bundles _astack_lib so modular tools work standalone
        copy_dir = self.dir / "user-bin-copy"
        copied = run("astack-tools", "link-bin", "--bin-dir", str(copy_dir), "--copy")
        self.assertEqual(copied.returncode, 0, copied.stderr)
        self.assertTrue((copy_dir / "astack-tools").is_file())
        self.assertFalse((copy_dir / "astack-tools").is_symlink())
        self.assertTrue((copy_dir / "_astack_lib" / "astack_tickets" / "cli.py").is_file())

        # Both launcher mode and --copy standalone mode execute modular astack-watch-tickets cleanly
        for target_bin in (bin_dir / "astack-watch-tickets", copy_dir / "astack-watch-tickets"):
            res = subprocess.run([sys.executable, "-B", str(target_bin), "--help"], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"{target_bin}: {res.stderr}")
            self.assertIn("astack-watch-tickets", res.stdout)

    def test_link_bin_launchers_follow_an_update_that_removes_the_linked_folder(self):
        home = self.dir / "home"

        def install(root, version, word):
            (root / "bin").mkdir(parents=True)
            (root / "skills" / "go").mkdir(parents=True)
            (root / "skills" / "go" / "SKILL.md").write_text("go\n")
            (root / ".claude-plugin").mkdir()
            (root / ".claude-plugin" / "plugin.json").write_text(json.dumps({"name": "astack", "version": version}))
            shutil.copy2(BIN / "astack-tools", root / "bin" / "astack-tools")
            script = root / "bin" / "astack-status"
            script.write_text(f"#!/bin/sh\necho {word} \"$@\"\n")
            script.chmod(0o755)

        old = home / ".claude" / "plugins" / "cache" / "market" / "astack" / "0.7.15"
        install(old, "0.7.15", "old")
        bin_dir = self.dir / "launcher-bin"
        env = {**os.environ, "HOME": str(home)}
        linked = subprocess.run([sys.executable, str(old / "bin" / "astack-tools"), "link-bin", "--bin-dir", str(bin_dir)], capture_output=True, text=True, env=env)
        self.assertEqual(linked.returncode, 0, linked.stderr)
        run_status = lambda: subprocess.run([str(bin_dir / "astack-status"), "x"], capture_output=True, text=True, env=env)
        self.assertEqual(run_status().stdout.strip(), "old x")
        # An update installs a newer copy elsewhere and the host removes the one it was linked from.
        new = home / ".local" / "share" / "kiln" / "agents" / "skills" / "pkgs" / "p-1234"
        install(new, "0.7.16", "new")
        shutil.rmtree(old)
        self.assertEqual(run_status().stdout.strip(), "new x")
        # The newest of two wins, not the first found.
        newer = home / ".claude" / "plugins" / "cache" / "market" / "astack" / "0.7.17"
        install(newer, "0.7.17", "newest")
        self.assertEqual(run_status().stdout.strip(), "newest x")
        # Nothing installed: it says so.
        shutil.rmtree(new)
        shutil.rmtree(newer)
        gone = run_status()
        self.assertNotEqual(gone.returncode, 0)
        self.assertIn("no installed astack found", gone.stderr)

    def test_skills_list_names_a_roles_required_skills_and_the_ones_for_when_the_work_calls(self):
        listing = run("astack-tools", "skills", "list", "--role", "reviewer")
        self.assertEqual(listing.returncode, 0, listing.stderr)
        required, _, applies = listing.stdout.partition("WHEN THE WORK CALLS FOR IT")
        for name in ("go", "adversarial-review", "rtfm", "prove-it", "blast-radius"):
            self.assertRegex(required, rf"(?m)^  {name}: ")
        self.assertRegex(applies, r"(?m)^  safe-to-rerun: ")
        self.assertNotRegex(listing.stdout, r"(?m)^  status: ", "a lead's skill isn't the reviewer's")
        self.assertIn("Use ", listing.stdout, "each line says when to load it")
        self.assertEqual(run("astack-tools", "skills", "list").returncode, 2)

    def test_skills_list_and_go_mode_promote_analyze_environment_when_project_astack_dir_missing(self):
        astack_home = self.dir / "astack-first-run-home"
        repo = self.dir / "FreshProj"
        repo.mkdir()
        git(repo, "init", "-q", "-b", "main")
        commit(repo, "README.md", "hello")
        wt = self.dir / "wt-lane-1"
        git(repo, "worktree", "add", "-q", "-b", "lane/one", str(wt))

        env = {**os.environ, "ASTACK_HOME": str(astack_home)}

        # 1. Before ~/.astack/freshproj/ exists: all 4 roles see analyze-environment under REQUIRED (even from worktree!)
        for role in ("lead", "worker", "reviewer", "researcher"):
            res = subprocess.run(
                [sys.executable, "-B", str(BIN / "astack-tools"), "skills", "list", "--role", role, "--cwd", str(wt)],
                capture_output=True, text=True, env=env,
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertIn("First astack run detected for project 'freshproj'", res.stdout)
            required, _, _ = res.stdout.partition("WHEN THE WORK CALLS FOR IT")
            self.assertRegex(required, r"(?m)^  analyze-environment: ", f"{role} should require analyze-environment on first run")

        # 2. Go-mode hook emits the first-run notice once on /astack:go activation in a new project (worktree-aware)
        state_root = self.dir / "state-first-run"
        hook_env = {**env, "ASTACK_STATE_DIR": str(state_root)}
        h_first = subprocess.run(
            [str(BIN / "astack-go-hook"), "--harness", "claude-code", "--event", "UserPromptSubmit"],
            input=json.dumps({"session_id": "fr-1", "prompt": "/astack:go inspect api", "cwd": str(wt)}),
            capture_output=True, text=True, env=hook_env,
        )
        self.assertEqual(h_first.returncode, 0, h_first.stderr)
        ctx = json.loads(h_first.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("astack first run", ctx)
        self.assertIn("analyze-environment", ctx)
        self.assertIn("freshproj", ctx)

        # 3. Once ~/.astack/freshproj/ exists: lead/worker/reviewer return analyze-environment to WHEN THE WORK CALLS FOR IT
        (astack_home / "freshproj").mkdir(parents=True)
        for role in ("lead", "worker", "reviewer"):
            res_after = subprocess.run(
                [sys.executable, "-B", str(BIN / "astack-tools"), "skills", "list", "--role", role, "--cwd", str(wt)],
                capture_output=True, text=True, env=env,
            )
            self.assertEqual(res_after.returncode, 0, res_after.stderr)
            self.assertNotIn("First astack run detected", res_after.stdout)
            _, _, applies = res_after.stdout.partition("WHEN THE WORK CALLS FOR IT")
            self.assertRegex(applies, r"(?m)^  analyze-environment: ", f"{role} should move analyze-environment back to situational")

        # Researcher always keeps analyze-environment under REQUIRED (no first-run banner once project dir exists)
        res_res = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "skills", "list", "--role", "researcher", "--cwd", str(wt)],
            capture_output=True, text=True, env=env,
        )
        self.assertNotIn("First astack run detected", res_res.stdout)
        req_res, _, _ = res_res.stdout.partition("WHEN THE WORK CALLS FOR IT")
        self.assertRegex(req_res, r"(?m)^  analyze-environment: ")

        # Go-mode hook stays quiet on /astack:go activation once ~/.astack/freshproj/ exists
        h_after = subprocess.run(
            [str(BIN / "astack-go-hook"), "--harness", "claude-code", "--event", "UserPromptSubmit"],
            input=json.dumps({"session_id": "fr-2", "prompt": "/astack:go inspect api", "cwd": str(wt)}),
            capture_output=True, text=True, env=hook_env,
        )
        self.assertEqual(h_after.returncode, 0, h_after.stderr)
        self.assertEqual(h_after.stdout.strip(), "")

    def test_skills_get_prints_one_skill_in_full_and_says_where_it_ends(self):
        got = run("astack-tools", "skills", "get", "prove-it")
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertIn((SKILLS / "prove-it" / "SKILL.md").read_text().strip(), got.stdout)
        self.assertRegex(got.stdout.rstrip().splitlines()[-1], r"^\[end of prove-it: \d+ characters")
        self.assertEqual(run("astack-tools", "skills", "get", "/astack:prove-it").returncode, 0)
        missing = run("astack-tools", "skills", "get", "not-a-skill")
        self.assertEqual(missing.returncode, 1)
        self.assertIn("not-a-skill", missing.stderr)

    def test_every_skill_fits_one_get_under_a_tools_output_limit(self):
        # Claude Code middle-truncates shell output past 30,000 chars, and Antigravity truncates SKILL.md bodies past 24,000 bytes.
        for folder in sorted(SKILLS.iterdir()):
            text = (folder / "SKILL.md").read_text()
            self.assertLess(len(text) + 600, 30000, f"{folder.name} is too long for one `skills get`")
            body = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.S)
            self.assertLess(len(body.encode("utf-8")), 24000, f"{folder.name} body exceeds Antigravity's 24,000-byte load cap")

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

    def test_init_home_and_lessons_commands_enforce_cross_platform_paths_permissions_and_filtering(self):
        fake_home = self.dir / "userhome"
        fake_home.mkdir()
        env = {**os.environ, "HOME": str(fake_home)}
        env.pop("ASTACK_HOME", None)

        def run_tools(*args, extra_env=None):
            e = {**env, **(extra_env or {})}
            return subprocess.run([sys.executable, "-B", str(BIN / "astack-tools"), *args], capture_output=True, text=True, env=e)

        # doctor reports missing ~/.astack before init-home without creating it
        doc_before = run_tools("doctor", "--venv", str(self.dir / "no-venv"), "--json")
        self.assertEqual(doc_before.returncode, 1)
        doc_data = json.loads(doc_before.stdout)
        self.assertEqual(doc_data["astack_home"]["path"], str(fake_home / ".astack"))
        self.assertFalse(doc_data["astack_home"]["exists"])

        # dry-run does not create ~/.astack
        dry = run_tools("init-home", "--dry-run", "--json")
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertFalse((fake_home / ".astack").exists())

        # init-home creates $HOME/.astack with owner-only 0o700 permissions on POSIX and is idempotent
        init_res = run_tools("init-home", "--json")
        self.assertEqual(init_res.returncode, 0, init_res.stderr)
        init_data = json.loads(init_res.stdout)
        self.assertTrue(init_data["created"])
        self.assertTrue(init_data["writable"])
        astack_home = fake_home / ".astack"
        self.assertTrue(astack_home.is_dir())
        if os.name != "nt":
            self.assertEqual(astack_home.stat().st_mode & 0o777, 0o700)

        init_again = run_tools("init-home", "--json")
        self.assertEqual(init_again.returncode, 0, init_again.stderr)
        self.assertFalse(json.loads(init_again.stdout)["created"])

        # init-home fails cleanly when target path is a regular file
        blocker = self.dir / "not-a-dir"
        blocker.write_text("file\n", encoding="utf-8")
        bad_home = run_tools("init-home", extra_env={"ASTACK_HOME": str(blocker)})
        self.assertEqual(bad_home.returncode, 1)
        self.assertIn("not a directory", bad_home.stderr)

        # lessons path --ensure creates ~/.astack/<project>/lessons/<lesson>/LESSON.md with 0o700 dirs
        p1 = run_tools("lessons", "path", "api-gateway", "tls-handshake-timeout", "--ensure")
        self.assertEqual(p1.returncode, 0, p1.stderr)
        lesson1 = Path(p1.stdout.strip())
        self.assertEqual(lesson1, astack_home / "api-gateway" / "lessons" / "tls-handshake-timeout" / "LESSON.md")
        self.assertTrue(lesson1.parent.is_dir())
        if os.name != "nt":
            self.assertEqual(lesson1.parent.stat().st_mode & 0o777, 0o700)

        p2 = run_tools("lessons", "path", "edge-iac", "waf-rule-order", "--ensure")
        self.assertEqual(p2.returncode, 0, p2.stderr)
        lesson2 = Path(p2.stdout.strip())

        p3 = run_tools("lessons", "path", "api-gateway", "old-retry-loop", "--ensure")
        self.assertEqual(p3.returncode, 0, p3.stderr)
        lesson3 = Path(p3.stdout.strip())

        lesson1.write_text(
            "---\n"
            "lesson: tls-handshake-timeout\n"
            "project: api-gateway\n"
            "related_projects: [edge-iac, auth-service]\n"
            "keywords: [tls, timeout, mtls]\n"
            "status: active\n"
            "created: 2026-11-25T10:00Z\n"
            "updated: 2026-11-25T12:00Z\n"
            "---\n\n"
            "# TLS Handshake Timeout Under Burst Load\n",
            encoding="utf-8",
            newline="\n",
        )
        lesson2.write_text(
            "---\n"
            "lesson: waf-rule-order\n"
            "project: edge-iac\n"
            "related_projects:\n"
            "  - api-gateway\n"
            "keywords:\n"
            "  - waf\n"
            "  - terraform\n"
            "status: active\n"
            "created: 2026-11-24T08:00Z\n"
            "updated: 2026-11-24T09:00Z\n"
            "---\n\n"
            "# WAF Rule Priority Must Preceding Rate Limits\n",
            encoding="utf-8",
            newline="\n",
        )
        lesson3.write_text(
            "---\n"
            "lesson: old-retry-loop\n"
            "project: api-gateway\n"
            "related_projects: []\n"
            "keywords: [retry]\n"
            "status: superseded\n"
            "created: 2026-11-01T08:00Z\n"
            "updated: 2026-11-20T09:00Z\n"
            "---\n\n"
            "# Retired Retry Loop\n",
            encoding="utf-8",
            newline="\n",
        )

        # lessons list parses frontmatter, supports --related for cross-repo discovery, --keyword, and --status
        all_list = run_tools("lessons", "list", "--json")
        self.assertEqual(all_list.returncode, 0, all_list.stderr)
        all_items = json.loads(all_list.stdout)["lessons"]
        self.assertEqual(len(all_items), 3)

        rel_auth = run_tools("lessons", "list", "--related", "auth-service", "--json")
        self.assertEqual(rel_auth.returncode, 0, rel_auth.stderr)
        rel_items = json.loads(rel_auth.stdout)["lessons"]
        self.assertEqual([(i["project"], i["lesson"]) for i in rel_items], [("api-gateway", "tls-handshake-timeout")])
        self.assertEqual(rel_items[0]["related_projects"], ["edge-iac", "auth-service"])
        self.assertEqual(rel_items[0]["keywords"], ["tls", "timeout", "mtls"])
        self.assertEqual(rel_items[0]["updated"], "2026-11-25T12:00Z")

        rel_gw = run_tools("lessons", "list", "--related", "api-gateway", "--status", "active", "--json")
        self.assertEqual(rel_gw.returncode, 0, rel_gw.stderr)
        self.assertEqual(
            [(i["project"], i["lesson"]) for i in json.loads(rel_gw.stdout)["lessons"]],
            [("api-gateway", "tls-handshake-timeout"), ("edge-iac", "waf-rule-order")],
        )

        kw_res = run_tools("lessons", "list", "--keyword", "terraform", "--json")
        self.assertEqual(kw_res.returncode, 0, kw_res.stderr)
        self.assertEqual([i["lesson"] for i in json.loads(kw_res.stdout)["lessons"]], ["waf-rule-order"])

        # Cross-platform slug validation rejects traversal, uppercase, separators, Windows reserved device names, and overlong slugs
        for bad_args in (
            ("lessons", "path", "../escape", "x"),
            ("lessons", "path", "proj", "a/b"),
            ("lessons", "path", "UpperCase", "ok"),
            ("lessons", "path", "con", "ok"),
            ("lessons", "path", "proj", "nul"),
            ("lessons", "path", "proj", "com1.log"),
            ("lessons", "path", "proj", "lpt9"),
            ("lessons", "path", "a" * 101, "ok"),
        ):
            bad = run_tools(*bad_args)
            self.assertEqual(bad.returncode, 2, f"expected slug rejection for {bad_args}: {bad.stdout} {bad.stderr}")

        # Symlink escape outside ~/.astack is refused
        if os.name != "nt":
            outside = self.dir / "outside"
            outside.mkdir()
            (astack_home / "escape-proj").symlink_to(outside)
            esc = run_tools("lessons", "path", "escape-proj", "bad", "--ensure")
            self.assertEqual(esc.returncode, 1)
            self.assertIn("outside astack home", esc.stderr)


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


class GoModeHookTest(Scratch):
    def _run_hook(self, script, args, payload, state_root):
        env = {**os.environ, "ASTACK_STATE_DIR": str(state_root)}
        cmd = [str(BIN / script), *args] if script.endswith("-hook") else [sys.executable, "-B", str(BIN / script), *args]
        return subprocess.run(cmd, input=json.dumps(payload), capture_output=True, text=True, env=env)

    def test_claude_code_sticky_go_mode_persists_across_prompts_compaction_and_exits_cleanly(self):
        state_root = self.dir / "state"
        sid = "claude-sess-1"

        # 1. Turn 1: /astack:go activates without duplicating reminder on that turn
        r1 = self._run_hook(
            "astack-go-hook", ["--harness", "claude-code", "--event", "UserPromptSubmit"],
            {"session_id": sid, "prompt": "/astack:go fix the retry bug"},
            state_root,
        )
        self.assertEqual(r1.returncode, 0, r1.stderr)
        self.assertEqual(r1.stdout.strip(), "")

        # 2. Turn 2 (after task finished): plain follow-up prompt injects Lead + Go mode reminder!
        r2 = self._run_hook(
            "astack-go-hook", ["--harness", "claude-code", "--event", "UserPromptSubmit"],
            {"session_id": sid, "prompt": "Now add caching to the user service"},
            state_root,
        )
        self.assertEqual(r2.returncode, 0, r2.stderr)
        out2 = json.loads(r2.stdout)
        ctx2 = out2["hookSpecificOutput"]["additionalContext"]
        self.assertIn("astack Go mode — ACTIVE (Lead role)", ctx2)
        self.assertIn("astack:worker", ctx2)
        self.assertIn("bugbash", ctx2)

        # 3. Unrelated session B is NOT affected (strict session isolation)
        r_other = self._run_hook(
            "astack-go-hook", ["--harness", "claude-code", "--event", "UserPromptSubmit"],
            {"session_id": "claude-sess-other", "prompt": "Say hello"},
            state_root,
        )
        self.assertEqual(r_other.returncode, 0)
        self.assertEqual(r_other.stdout.strip(), "")

        # 4. Compaction (SessionStart source=compact) re-injects with reload instruction
        r_cmp = self._run_hook(
            "astack-go-hook", ["--harness", "claude-code", "--event", "SessionStart"],
            {"session_id": sid, "source": "compact"},
            state_root,
        )
        self.assertEqual(r_cmp.returncode, 0)
        ctx_cmp = json.loads(r_cmp.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("compacted/resumed", ctx_cmp)
        self.assertIn("SKILL.md", ctx_cmp)

        # 5. Explicit exit deactivates Go mode; subsequent prompts stay quiet
        r_exit = self._run_hook(
            "astack-go-hook", ["--harness", "claude-code", "--event", "UserPromptSubmit"],
            {"session_id": sid, "prompt": "exit go mode"},
            state_root,
        )
        self.assertEqual(r_exit.returncode, 0)
        self.assertIn("EXITED", json.loads(r_exit.stdout)["hookSpecificOutput"]["additionalContext"])

        r_after = self._run_hook(
            "astack-go-hook", ["--harness", "claude-code", "--event", "UserPromptSubmit"],
            {"session_id": sid, "prompt": "Just answer a quick question"},
            state_root,
        )
        self.assertEqual(r_after.stdout.strip(), "")

        # 6. Auto-load via PostToolUse Skill(astack:go) activates, while subagent listing --role worker is ignored
        sid_auto = "claude-sess-auto"
        r_auto = self._run_hook(
            "astack-go-hook", ["--harness", "claude-code", "--event", "PostToolUse"],
            {"session_id": sid_auto, "tool_name": "Skill", "tool_input": {"skill": "astack:go"}},
            state_root,
        )
        self.assertEqual(r_auto.returncode, 0)
        r_auto_next = self._run_hook(
            "astack-go-hook", ["--harness", "claude-code", "--event", "UserPromptSubmit"],
            {"session_id": sid_auto, "prompt": "Now review this diff"},
            state_root,
        )
        self.assertIn("ACTIVE (Lead role)", json.loads(r_auto_next.stdout)["hookSpecificOutput"]["additionalContext"])

        # Clear resets session cleanly
        self._run_hook(
            "astack-go-hook", ["--harness", "claude-code", "--event", "SessionStart"],
            {"session_id": sid_auto, "source": "clear"},
            state_root,
        )
        r_cleared = self._run_hook(
            "astack-go-hook", ["--harness", "claude-code", "--event", "UserPromptSubmit"],
            {"session_id": sid_auto, "prompt": "Fresh start"},
            state_root,
        )
        self.assertEqual(r_cleared.stdout.strip(), "")

        # Subagent session running `astack-tools skills list --role worker` never activates Lead Go mode
        sid_sub = "claude-sub-worker"
        self._run_hook(
            "astack-go-hook", ["--harness", "claude-code", "--event", "PostToolUse"],
            {"session_id": sid_sub, "tool_name": "Bash", "tool_input": {"command": "astack-tools skills list --role worker"}},
            state_root,
        )
        self._run_hook(
            "astack-go-hook", ["--harness", "claude-code", "--event", "PostToolUse"],
            {"session_id": sid_sub, "tool_name": "Bash", "tool_input": {"command": "astack-tools skills get go"}},
            state_root,
        )
        r_sub = self._run_hook(
            "astack-go-hook", ["--harness", "claude-code", "--event", "UserPromptSubmit"],
            {"session_id": sid_sub, "prompt": "continue"},
            state_root,
        )
        self.assertEqual(r_sub.stdout.strip(), "")

    def test_antigravity_codex_and_cursor_hook_contracts(self):
        state_root = self.dir / "state-multi"

        # Antigravity: PostToolUse fast-path returns {}, PreInvocation injects ONCE per new prompt and on compaction
        ag_sid = "agy-conv-1"
        ag_noop = self._run_hook(
            "astack-go-hook", ["--harness", "antigravity", "--event", "PostToolUse"],
            {"conversationId": ag_sid, "toolCall": {"name": "read_file", "args": {"Path": "/tmp/foo.py"}}},
            state_root,
        )
        self.assertEqual(ag_noop.returncode, 0)
        self.assertEqual(json.loads(ag_noop.stdout), {})

        ag_act = self._run_hook(
            "astack-go-hook", ["--harness", "antigravity", "--event", "PreInvocation"],
            {"conversationId": ag_sid, "lastUserInput": "/astack-go fix login", "initialNumSteps": 2},
            state_root,
        )
        self.assertEqual(json.loads(ag_act.stdout), {})

        # Same turn, later model call -> no duplicate injection
        ag_same = self._run_hook(
            "astack-go-hook", ["--harness", "antigravity", "--event", "PreInvocation"],
            {"conversationId": ag_sid, "lastUserInput": "/astack-go fix login", "initialNumSteps": 10},
            state_root,
        )
        self.assertEqual(json.loads(ag_same.stdout), {})

        # New user prompt -> injects systemMessage ONCE
        ag_next = self._run_hook(
            "astack-go-hook", ["--harness", "antigravity", "--event", "PreInvocation"],
            {"conversationId": ag_sid, "lastUserInput": "Now update the docs", "initialNumSteps": 12},
            state_root,
        )
        ag_out = json.loads(ag_next.stdout)
        self.assertIn("ACTIVE (Lead role)", ag_out["injectSteps"][0]["systemMessage"]["systemMessage"])
        self.assertIn("astack-worker", ag_out["injectSteps"][0]["systemMessage"]["systemMessage"])

        # Same new prompt, next model call -> quiet again
        ag_next2 = self._run_hook(
            "astack-go-hook", ["--harness", "antigravity", "--event", "PreInvocation"],
            {"conversationId": ag_sid, "lastUserInput": "Now update the docs", "initialNumSteps": 15},
            state_root,
        )
        self.assertEqual(json.loads(ag_next2.stdout), {})

        # Trajectory shrinks (compaction) -> re-injects with compaction note
        ag_cmp = self._run_hook(
            "astack-go-hook", ["--harness", "antigravity", "--event", "PreInvocation"],
            {"conversationId": ag_sid, "lastUserInput": "Now update the docs", "initialNumSteps": 3},
            state_root,
        )
        self.assertIn("compacted/resumed", json.loads(ag_cmp.stdout)["injectSteps"][0]["systemMessage"]["systemMessage"])

        # Codex: $astack-go activates and follow-up returns hookSpecificOutput.additionalContext
        cx_sid = "codex-sess-1"
        self._run_hook(
            "astack-go-hook", ["--harness", "codex", "--event", "UserPromptSubmit"],
            {"session_id": cx_sid, "prompt": "$astack-go build parser"},
            state_root,
        )
        cx_next = self._run_hook(
            "astack-go-hook", ["--harness", "codex", "--event", "UserPromptSubmit"],
            {"session_id": cx_sid, "prompt": "Now optimize it"},
            state_root,
        )
        self.assertIn("astack-worker", json.loads(cx_next.stdout)["hookSpecificOutput"]["additionalContext"])

        # Cursor: beforeSubmitPrompt returns {"continue": true} and sessionStart resumes with additional_context
        cur_sid = "cursor-conv-1"
        cur_p1 = self._run_hook(
            "astack-go-hook", ["--harness", "cursor", "--event", "beforeSubmitPrompt"],
            {"conversation_id": cur_sid, "prompt": "/astack-go refactor api"},
            state_root,
        )
        self.assertEqual(json.loads(cur_p1.stdout), {"continue": True})
        cur_resume = self._run_hook(
            "astack-go-hook", ["--harness", "cursor", "--event", "sessionStart"],
            {"conversation_id": cur_sid},
            state_root,
        )
        self.assertIn("ACTIVE (Lead role)", json.loads(cur_resume.stdout)["additional_context"])

        # Explicit /astack:bap works even outside Go mode; repeated-reminder cues fire BAP inside Go mode without false-triggering normal prompts
        r_bap_out = self._run_hook(
            "astack-go-hook", ["--harness", "claude-code", "--event", "UserPromptSubmit"],
            {"session_id": "non-go-sess", "prompt": "/astack:bap you forgot to run tests again"},
            state_root,
        )
        self.assertIn("astack BAP", json.loads(r_bap_out.stdout)["hookSpecificOutput"]["additionalContext"])

        self._run_hook(
            "astack-go-hook", ["--harness", "claude-code", "--event", "UserPromptSubmit"],
            {"session_id": "go-bap-sess", "prompt": "/astack:go build auth"},
            state_root,
        )
        r_normal = self._run_hook(
            "astack-go-hook", ["--harness", "claude-code", "--event", "UserPromptSubmit"],
            {"session_id": "go-bap-sess", "prompt": "Add rate limiting next"},
            state_root,
        )
        self.assertNotIn("astack BAP", json.loads(r_normal.stdout)["hookSpecificOutput"]["additionalContext"])

        r_repeat = self._run_hook(
            "astack-go-hook", ["--harness", "claude-code", "--event", "UserPromptSubmit"],
            {"session_id": "go-bap-sess", "prompt": "I already told you to update the README when flags change"},
            state_root,
        )
        repeat_ctx = json.loads(r_repeat.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("astack BAP", repeat_ctx)
        self.assertIn("astack Go mode — ACTIVE (Lead role)", repeat_ctx)

    def test_hook_launchers_survive_empty_path_and_fail_open_without_python(self):
        state_root = self.dir / "state-empty-path"
        empty_path_env = {
            "PATH": "",
            "HOME": str(self.dir),
            "ASTACK_STATE_DIR": str(state_root),
            "ASTACK_HOME": str(self.dir / "astack-home"),
        }

        # 1. With PATH="", astack-go-hook still restores standard paths, activates Go mode, and injects on follow-up
        r1 = subprocess.run(
            [str(BIN / "astack-go-hook"), "--harness", "claude-code", "--event", "UserPromptSubmit"],
            input=json.dumps({"session_id": "empty-path-cc", "prompt": "/astack:go fix cache"}),
            capture_output=True, text=True, env=empty_path_env,
        )
        self.assertEqual(r1.returncode, 0, r1.stderr)
        r2 = subprocess.run(
            [str(BIN / "astack-go-hook"), "--harness", "claude-code", "--event", "UserPromptSubmit"],
            input=json.dumps({"session_id": "empty-path-cc", "prompt": "Now add tests"}),
            capture_output=True, text=True, env=empty_path_env,
        )
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertIn("ACTIVE (Lead role)", json.loads(r2.stdout)["hookSpecificOutput"]["additionalContext"])

        # 2. With PATH="", astack-stamp-hook actually stamps LANES.md instead of silently skipping it
        lane_log = self.dir / "LANES.md"
        lane_log.write_text("<!-- astack lane log -->\n\n## Log\nstarted worker-a on cache\n", encoding="utf-8")
        r_stamp = subprocess.run(
            [str(BIN / "astack-stamp-hook")],
            input=json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(lane_log)}}),
            capture_output=True, text=True, env=empty_path_env,
        )
        self.assertEqual(r_stamp.returncode, 0, r_stamp.stderr)
        self.assertRegex(
            lane_log.read_text(encoding="utf-8").splitlines()[-1],
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z started worker-a on cache$",
        )

        # 3. When Python is missing or crashes, both hooks fail open (exit 0) with valid harness-native JSON
        for broken_py in ("/nonexistent/astack-python3", "/usr/bin/false"):
            no_py_env = {**empty_path_env, "ASTACK_PYTHON": broken_py}
            r_cc = subprocess.run(
                [str(BIN / "astack-go-hook"), "--harness", "claude-code", "--event", "UserPromptSubmit"],
                input=json.dumps({"session_id": "nopy", "prompt": "hello"}),
                capture_output=True, text=True, env=no_py_env,
            )
            self.assertEqual(r_cc.returncode, 0, f"{broken_py}: {r_cc.stderr}")
            self.assertEqual(r_cc.stdout.strip(), "")

            r_ag = subprocess.run(
                [str(BIN / "astack-go-hook"), "--harness", "antigravity", "--event", "PreInvocation"],
                input=json.dumps({"conversationId": "nopy-ag", "lastUserInput": "hello"}),
                capture_output=True, text=True, env=no_py_env,
            )
            self.assertEqual(r_ag.returncode, 0, f"{broken_py}: {r_ag.stderr}")
            self.assertEqual(json.loads(r_ag.stdout), {})

            r_cur = subprocess.run(
                [str(BIN / "astack-go-hook"), "--harness", "cursor", "--event", "beforeSubmitPrompt"],
                input=json.dumps({"conversation_id": "nopy-cur", "prompt": "hello"}),
                capture_output=True, text=True, env=no_py_env,
            )
            self.assertEqual(r_cur.returncode, 0, f"{broken_py}: {r_cur.stderr}")
            self.assertEqual(json.loads(r_cur.stdout), {"continue": True})

            r_st = subprocess.run(
                [str(BIN / "astack-stamp-hook")],
                input=json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(lane_log)}}),
                capture_output=True, text=True, env=no_py_env,
            )
            self.assertEqual(r_st.returncode, 0, f"{broken_py}: {r_st.stderr}")

        # 4. Python entrypoint also fails open with valid JSON if state-dir is an unwritable file collision
        bad_state = self.dir / "not-a-dir"
        bad_state.write_text("file blocking mkdir", encoding="utf-8")
        r_bad = subprocess.run(
            [
                sys.executable, "-B", str(BIN / "astack-go-mode"),
                "--hook", "--harness", "cursor", "--event", "beforeSubmitPrompt",
                "--state-dir", str(bad_state),
            ],
            input=json.dumps({"conversation_id": "bad-state", "prompt": "/astack-go test"}),
            capture_output=True, text=True,
        )
        self.assertEqual(r_bad.returncode, 0, r_bad.stderr)
        self.assertEqual(json.loads(r_bad.stdout), {"continue": True})

    def test_auto_memory_recall_is_prompt_matched_non_anchoring_and_requires_explicit_active_status(self):
        state_root = self.dir / "state-lessons"
        astack_home = self.dir / "astack-home"
        ws = self.dir / "billing-api"
        ws.mkdir()

        # Direct active lesson, related-project active lesson, superseded lesson, and malformed (status-less) lesson
        l1 = astack_home / "billing-api" / "lessons" / "webhook-hmac" / "LESSON.md"
        l1.parent.mkdir(parents=True)
        l1.write_text(
            "---\nlesson: webhook-hmac\nproject: billing-api\nrelated_projects: []\n"
            "keywords: [webhook, hmac, signature]\nstatus: active\nupdated: 2026-11-25T12:00Z\n---\n\n"
            "# Webhook failures are always TLS\n",
            encoding="utf-8",
        )
        l2 = astack_home / "payments-gw" / "lessons" / "retry-idempotency" / "LESSON.md"
        l2.parent.mkdir(parents=True)
        l2.write_text(
            "---\nlesson: retry-idempotency\nproject: payments-gw\nrelated_projects: [billing-api]\n"
            "keywords: [retry, idempotency, webhook]\nstatus: active\nupdated: 2026-11-24T10:00Z\n---\n\n"
            "# Always cache failed receipts\n",
            encoding="utf-8",
        )
        l3 = astack_home / "billing-api" / "lessons" / "retired-xml" / "LESSON.md"
        l3.parent.mkdir(parents=True)
        l3.write_text(
            "---\nlesson: retired-xml\nproject: billing-api\nkeywords: [webhook]\nstatus: superseded\n---\n\n# Old XML\n",
            encoding="utf-8",
        )
        l4 = astack_home / "billing-api" / "lessons" / "malformed-no-status" / "LESSON.md"
        l4.parent.mkdir(parents=True)
        l4.write_text(
            "---\nlesson: malformed-no-status\nproject: billing-api\nkeywords: [webhook]\n---\n\n# Missing status\n",
            encoding="utf-8",
        )

        env = {**os.environ, "ASTACK_STATE_DIR": str(state_root), "ASTACK_HOME": str(astack_home)}

        # 1. SessionStart before task is known MUST stay silent (no blind dump of unrelated lessons)
        r_start = subprocess.run(
            [str(BIN / "astack-go-hook"), "--harness", "claude-code", "--event", "SessionStart"],
            input=json.dumps({"session_id": "recall-1", "source": "startup", "cwd": str(ws)}),
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(r_start.returncode, 0, r_start.stderr)
        self.assertEqual(r_start.stdout.strip(), "")

        # 2. Unrelated prompt MUST inject nothing
        r_unrel = subprocess.run(
            [str(BIN / "astack-go-hook"), "--harness", "claude-code", "--event", "UserPromptSubmit"],
            input=json.dumps({"session_id": "recall-1", "prompt": "Refactor the CSS button padding", "cwd": str(ws)}),
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(r_unrel.returncode, 0, r_unrel.stderr)
        self.assertEqual(r_unrel.stdout.strip(), "")

        # 3. Relevant prompt surfaces ONLY matching explicit status:active slugs/keywords/paths — NEVER H1 conclusions!
        r_match = subprocess.run(
            [str(BIN / "astack-go-hook"), "--harness", "claude-code", "--event", "UserPromptSubmit"],
            input=json.dumps({"session_id": "recall-1", "prompt": "Debug webhook signature 400 errors", "cwd": str(ws)}),
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(r_match.returncode, 0, r_match.stderr)
        ctx = json.loads(r_match.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("billing-api/webhook-hmac", ctx)
        self.assertIn("payments-gw/retry-idempotency", ctx)
        self.assertIn("unverified hypotheses", ctx)
        self.assertNotIn("Webhook failures are always TLS", ctx)
        self.assertNotIn("Always cache failed receipts", ctx)
        self.assertNotIn("retired-xml", ctx)
        self.assertNotIn("malformed-no-status", ctx)

        # 4. Antigravity PreInvocation surfaces matching lessons once per prompt without H1 titles
        r_ag = subprocess.run(
            [str(BIN / "astack-go-hook"), "--harness", "antigravity", "--event", "PreInvocation"],
            input=json.dumps({
                "conversationId": "ag-recall-1",
                "lastUserInput": "Investigate retry idempotency timeout",
                "workspacePaths": [str(ws)],
            }),
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(r_ag.returncode, 0, r_ag.stderr)
        ag_msg = json.loads(r_ag.stdout)["injectSteps"][0]["systemMessage"]["systemMessage"]
        self.assertIn("payments-gw/retry-idempotency", ag_msg)
        self.assertNotIn("billing-api/webhook-hmac", ag_msg)
        self.assertNotIn("Always cache failed receipts", ag_msg)

        # 5. CLI `astack-go-mode lessons --cwd ... --query ... --json` matches cleanly and skips status-less lessons
        r_cli = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-go-mode"), "lessons", "--cwd", str(ws), "--query", "hmac", "--json"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(r_cli.returncode, 0, r_cli.stderr)
        data = json.loads(r_cli.stdout)
        self.assertEqual(data["project"], "billing-api")
        self.assertEqual([x["lesson"] for x in data["lessons"]], ["webhook-hmac"])

    def test_arch_path_resolves_cross_os_astack_home_and_increments_ad_numbers(self):
        astack_home = self.dir / "astack-home"
        env = {**os.environ, "ASTACK_HOME": str(astack_home)}

        # --next --ensure creates <ASTACK_HOME>/<project>/architecture/ and starts at AD_1.md
        r1 = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "arch", "path", "hyperscale", "--next", "--ensure"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(r1.returncode, 0, r1.stderr)
        p1 = Path(r1.stdout.strip())
        self.assertEqual(p1, astack_home / "hyperscale" / "architecture" / "AD_1.md")
        self.assertTrue(p1.parent.is_dir())

        # Writing AD_1.md and AD_3.md -> --next advances to AD_4.md, and arch list reads frontmatter + status
        p1.write_text("---\nad_number: 1\nname: Event Ledger\ndescription: Append-only ledger\n---\n\n# AD-1: Event Ledger\n\n## Status\n\nAccepted (2026-11-25).\n")
        (p1.parent / "AD_3.md").write_text("---\nad_number: 3\nname: Lease Fencing\ndescription: Monotonic tokens\n---\n\n# AD-3: Lease Fencing\n\n## Status\n\nBuilt (2026-11-25).\n")
        r2 = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "arch", "path", "hyperscale", "--next"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertEqual(Path(r2.stdout.strip()), p1.parent / "AD_4.md")

        r_list = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "arch", "list", "--project", "hyperscale", "--json"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(r_list.returncode, 0, r_list.stderr)
        listed = json.loads(r_list.stdout)["decisions"]
        self.assertEqual([d["ad_number"] for d in listed], [1, 3])
        self.assertEqual(listed[0]["name"], "Event Ledger")
        self.assertEqual(listed[0]["status"], "Accepted (2026-11-25).")
        self.assertEqual(listed[1]["status"], "Built (2026-11-25).")

        # Explicit number & path-traversal rejection
        r_num = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "arch", "path", "hyperscale", "26"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(r_num.returncode, 0, r_num.stderr)
        self.assertEqual(Path(r_num.stdout.strip()), p1.parent / "AD_26.md")

        r_bad = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "arch", "path", "../escape", "--next"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(r_bad.returncode, 2)

    def test_reviews_path_and_list_manage_cross_os_timestamped_evidence_bundles(self):
        astack_home = self.dir / "astack-reviews-home"
        env = {**os.environ, "ASTACK_HOME": str(astack_home)}

        # --new --ensure creates private <ASTACK_HOME>/<project>/reviews/<YYYY-MM-DDTHH-MM-SSZ>
        r1 = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "reviews", "path", "payments", "--new", "--ensure"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(r1.returncode, 0, r1.stderr)
        b1 = Path(r1.stdout.strip())
        self.assertEqual(b1.parent, astack_home / "payments" / "reviews")
        self.assertTrue(b1.is_dir())
        if os.name != "nt":
            self.assertEqual(b1.stat().st_mode & 0o777, 0o700)

        # Second --new --ensure never collides with an existing bundle directory
        r2 = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "reviews", "path", "payments", "--new", "--ensure"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(r2.returncode, 0, r2.stderr)
        b2 = Path(r2.stdout.strip())
        self.assertNotEqual(b1, b2)
        self.assertTrue(b2.is_dir())

        # Explicit Windows-safe timestamps sort newest-first in `reviews list`
        r_old = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "reviews", "path", "payments", "2026-11-24T10-00-00Z", "--ensure"],
            capture_output=True, text=True, env=env,
        )
        r_new = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "reviews", "path", "payments", "2026-11-25T16-30-00Z", "--ensure"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(r_old.returncode, 0, r_old.stderr)
        self.assertEqual(r_new.returncode, 0, r_new.stderr)
        old_dir = Path(r_old.stdout.strip())
        new_dir = Path(r_new.stdout.strip())

        (old_dir / "trace.json").write_text('{"spans": []}\n', encoding="utf-8")
        (old_dir / "REVIEW.md").write_text("VERDICT: BLOCKED: duplicate charge on retry\n", encoding="utf-8")
        (new_dir / "logs").mkdir()
        (new_dir / "logs" / "repro.log").write_text("PASS: idempotency key enforced\n", encoding="utf-8")
        (new_dir / "bench.txt").write_text("p99=12.4ms\n", encoding="utf-8")
        (new_dir / "ui.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (new_dir / ".tmp").mkdir()
        (new_dir / ".tmp" / "ignored.tmp").write_text("temp\n", encoding="utf-8")
        (new_dir / "audit-receipt.txt").write_text("Verdict: CLEAR\nEvidence: logs/repro.log, bench.txt\n", encoding="utf-8")

        r_list = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "reviews", "list", "--project", "payments", "--json"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(r_list.returncode, 0, r_list.stderr)
        bundles = json.loads(r_list.stdout)["reviews"]
        by_dt = {b["date_time"]: b for b in bundles}
        self.assertIn("2026-11-25T16-30-00Z", by_dt)
        self.assertIn("2026-11-24T10-00-00Z", by_dt)
        self.assertEqual(by_dt["2026-11-25T16-30-00Z"]["verdict"], "CLEAR")
        self.assertEqual(by_dt["2026-11-24T10-00-00Z"]["verdict"], "BLOCKED: duplicate charge on retry")
        self.assertEqual(
            by_dt["2026-11-25T16-30-00Z"]["artifacts"],
            ["audit-receipt.txt", "bench.txt", "logs/repro.log", "ui.png"],
        )

        # --limit bounds returned bundles newest-first
        r_lim = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "reviews", "list", "--project", "payments", "--limit", "1", "--json"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(r_lim.returncode, 0, r_lim.stderr)
        self.assertEqual(len(json.loads(r_lim.stdout)["reviews"]), 1)

        # Reject colons (Windows-unsafe), traversal, and reserved names
        for bad_args in (
            ("reviews", "path", "payments", "2026-11-25T16:30:00Z"),
            ("reviews", "path", "payments", "../escape"),
            ("reviews", "path", "payments", "nul"),
            ("reviews", "path", "../bad", "--new"),
        ):
            r_bad = subprocess.run(
                [sys.executable, "-B", str(BIN / "astack-tools"), *bad_args],
                capture_output=True, text=True, env=env,
            )
            self.assertEqual(r_bad.returncode, 2, f"expected exit 2 for {bad_args}")

        # Project-scoped repros: ~/.astack/<project>/repros/<repro>/
        rp = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "repros", "path", "payments", "retry-dup-charge", "--ensure"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(rp.returncode, 0, rp.stderr)
        repro_dir = Path(rp.stdout.strip())
        self.assertEqual(repro_dir, astack_home / "payments" / "repros" / "retry-dup-charge")
        self.assertTrue(repro_dir.is_dir())
        if os.name != "nt":
            self.assertEqual(repro_dir.stat().st_mode & 0o777, 0o700)
        (repro_dir / "repro.py").write_text("raise SystemExit(1)\n", encoding="utf-8")

        rp_list = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "repros", "list", "--project", "payments", "--json"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(rp_list.returncode, 0, rp_list.stderr)
        repro_items = json.loads(rp_list.stdout)["repros"]
        self.assertEqual(len(repro_items), 1)
        self.assertEqual(repro_items[0]["repro"], "retry-dup-charge")
        self.assertEqual(repro_items[0]["files"], ["repro.py"])

        rp_bad = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "repros", "path", "payments", "../escape"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(rp_bad.returncode, 2)

        # Project-scoped automations: ~/.astack/<project>/automations/<automation>/
        auto_wf = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "automations", "path", "payments", "release-check", "--ensure"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(auto_wf.returncode, 0, auto_wf.stderr)
        wf_dir = Path(auto_wf.stdout.strip())
        self.assertEqual(wf_dir, astack_home / "payments" / "automations" / "release-check")
        self.assertTrue(wf_dir.is_dir())
        if os.name != "nt":
            self.assertEqual(wf_dir.stat().st_mode & 0o777, 0o700)
        (wf_dir / "automation.json").write_text(
            json.dumps({
                "runner": "werkflow",
                "entrypoint": "workflow.py",
                "description": "Release verification pipeline",
                "modules": ["shell", "github"],
            }),
            encoding="utf-8",
        )
        (wf_dir / "workflow.py").write_text("from werkflow import Workflow\n", encoding="utf-8")
        (wf_dir / ".werkflow.json.example").write_text('{"project_options": {}}\n', encoding="utf-8")
        (wf_dir / ".tmp").mkdir()
        (wf_dir / ".tmp" / "scratch.txt").write_text("ignore\n", encoding="utf-8")
        (wf_dir / "__pycache__").mkdir()
        (wf_dir / "__pycache__" / "workflow.cpython-312.pyc").write_bytes(b"\x00")

        # Runner inferred from imports when automation.json is absent
        auto_orch = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "automations", "path", "payments", "nightly-dag", "--ensure"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(auto_orch.returncode, 0, auto_orch.stderr)
        orch_dir = Path(auto_orch.stdout.strip())
        (orch_dir / "workflow.py").write_text("from orchestral import Orchestral\n", encoding="utf-8")

        auto_task = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "automations", "path", "payments", "health-watch", "--ensure"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(auto_task.returncode, 0, auto_task.stderr)
        task_dir = Path(auto_task.stdout.strip())
        # TaskEx scripts can import werkflow-modules directly and must still classify as taskex
        (task_dir / "task.py").write_text(
            "from werkflow_github import Github\nfrom taskex import TaskRunner\n",
            encoding="utf-8",
        )

        a_list = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "automations", "list", "--project", "payments", "--json"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(a_list.returncode, 0, a_list.stderr)
        autos = {a["automation"]: a for a in json.loads(a_list.stdout)["automations"]}
        self.assertEqual(set(autos), {"release-check", "nightly-dag", "health-watch"})
        self.assertEqual(autos["release-check"]["runner"], "werkflow")
        self.assertEqual(autos["release-check"]["modules"], ["shell", "github"])
        self.assertEqual(
            autos["release-check"]["files"],
            [".werkflow.json.example", "automation.json", "workflow.py"],
        )
        self.assertEqual(autos["nightly-dag"]["runner"], "orchestral")
        self.assertEqual(autos["nightly-dag"]["entrypoint"], "workflow.py")
        self.assertEqual(autos["health-watch"]["runner"], "taskex")
        self.assertEqual(autos["health-watch"]["entrypoint"], "task.py")

        a_filtered = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "automations", "list", "--project", "payments", "--runner", "werkflow", "--json"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(a_filtered.returncode, 0, a_filtered.stderr)
        self.assertEqual([a["automation"] for a in json.loads(a_filtered.stdout)["automations"]], ["release-check"])

        for bad_auto in (
            ("automations", "path", "payments", "../escape"),
            ("automations", "path", "payments", "con"),
            ("automations", "path", "../bad", "ok"),
        ):
            a_bad = subprocess.run(
                [sys.executable, "-B", str(BIN / "astack-tools"), *bad_auto],
                capture_output=True, text=True, env=env,
            )
            self.assertEqual(a_bad.returncode, 2, f"expected exit 2 for {bad_auto}")

        # Project-scoped external research: ~/.astack/<project>/research/[subpath]/[file]
        res_p = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "research", "path", "payments", "rfc9110", "--file", "notes.md", "--ensure"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(res_p.returncode, 0, res_p.stderr)
        res_file = Path(res_p.stdout.strip())
        self.assertEqual(res_file, astack_home / "payments" / "research" / "rfc9110" / "notes.md")
        self.assertTrue(res_file.parent.is_dir())
        if os.name != "nt":
            self.assertEqual(res_file.parent.stat().st_mode & 0o777, 0o700)
        res_file.write_text("# RFC 9110 notes\n", encoding="utf-8")

        res_list = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "research", "list", "--project", "payments", "--json"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(res_list.returncode, 0, res_list.stderr)
        res_items = json.loads(res_list.stdout)["research"]
        self.assertEqual(len(res_items), 1)
        self.assertEqual(res_items[0]["name"], "rfc9110")
        self.assertEqual(res_items[0]["files"], ["notes.md"])

        # Project-scoped general docs (including docs/contracts/): ~/.astack/<project>/docs/[subdir]/[file]
        doc_p = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "docs", "path", "payments", "contracts", "--file", "cli.md", "--ensure"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(doc_p.returncode, 0, doc_p.stderr)
        doc_file = Path(doc_p.stdout.strip())
        self.assertEqual(doc_file, astack_home / "payments" / "docs" / "contracts" / "cli.md")
        self.assertTrue(doc_file.parent.is_dir())
        if os.name != "nt":
            self.assertEqual(doc_file.parent.stat().st_mode & 0o777, 0o700)
        doc_file.write_text("# CLI contracts\n", encoding="utf-8")

        doc_list = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "docs", "list", "--project", "payments", "--subdir", "contracts", "--json"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(doc_list.returncode, 0, doc_list.stderr)
        doc_items = json.loads(doc_list.stdout)["docs"]
        self.assertEqual(len(doc_items), 1)
        self.assertEqual(doc_items[0]["name"], "contracts/cli.md")

        # Project-scoped logging: ~/.astack/<project>/logging/<logs|traces|metrics>/[FILE_YYYY_MM_DD_HH_MM_SS]
        log_p = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "logging", "path", "payments", "logs", "checkout", "--ensure"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(log_p.returncode, 0, log_p.stderr)
        log_file = Path(log_p.stdout.strip())
        self.assertEqual(log_file.parent, astack_home / "payments" / "logging" / "logs")
        self.assertRegex(log_file.name, r"^checkout_\d{4}_\d{2}_\d{2}_\d{2}_\d{2}_\d{2}\.log$")
        log_file.write_text("line1\n", encoding="utf-8")

        tr_p = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "logging", "path", "payments", "traces", "api.json", "--ensure"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(tr_p.returncode, 0, tr_p.stderr)
        tr_file = Path(tr_p.stdout.strip())
        self.assertRegex(tr_file.name, r"^api_\d{4}_\d{2}_\d{2}_\d{2}_\d{2}_\d{2}\.json$")
        tr_file.write_text("{}\n", encoding="utf-8")

        # Explicit pre-stamped metrics file keeps exact name
        met_p = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "logging", "path", "payments", "metrics", "p99_2026_11_25_12_00_00.csv", "--ensure"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(met_p.returncode, 0, met_p.stderr)
        met_file = Path(met_p.stdout.strip())
        self.assertEqual(met_file.name, "p99_2026_11_25_12_00_00.csv")
        met_file.write_text("p99,12.3\n", encoding="utf-8")

        log_list = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "logging", "list", "--project", "payments", "--json"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(log_list.returncode, 0, log_list.stderr)
        log_items = json.loads(log_list.stdout)["logging"]
        self.assertEqual({i["kind"] for i in log_items}, {"logs", "traces", "metrics"})

        log_traces = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "logging", "list", "--project", "payments", "--kind", "traces", "--json"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(log_traces.returncode, 0, log_traces.stderr)
        self.assertEqual(len(json.loads(log_traces.stdout)["logging"]), 1)

        # --limit sorts newest-first by embedded UTC timestamp, NOT capture-name alphabetical prefix
        logs_dir = astack_home / "payments" / "logging" / "logs"
        for existing in list(logs_dir.iterdir()):
            existing.unlink()
        (logs_dir / "worker_2026_11_20_10_00_00.log").write_text("oldest\n", encoding="utf-8")
        (logs_dir / "checkout_2026_11_24_10_00_00.log").write_text("middle\n", encoding="utf-8")
        (logs_dir / "api_2026_11_25_10_00_00.log").write_text("newest\n", encoding="utf-8")

        log_newest = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "logging", "list", "--project", "payments", "--kind", "logs", "--limit", "1", "--json"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(log_newest.returncode, 0, log_newest.stderr)
        self.assertEqual(
            [e["file"] for e in json.loads(log_newest.stdout)["logging"]],
            ["api_2026_11_25_10_00_00.log"],
        )

        log_ordered = subprocess.run(
            [sys.executable, "-B", str(BIN / "astack-tools"), "logging", "list", "--project", "payments", "--kind", "logs", "--json"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(log_ordered.returncode, 0, log_ordered.stderr)
        self.assertEqual(
            [e["file"] for e in json.loads(log_ordered.stdout)["logging"]],
            [
                "api_2026_11_25_10_00_00.log",
                "checkout_2026_11_24_10_00_00.log",
                "worker_2026_11_20_10_00_00.log",
            ],
        )

        for bad_new in (
            ("research", "path", "payments", "../escape"),
            ("research", "path", "payments", "ok", "--file", "nul.md"),
            ("docs", "path", "payments", "contracts/../../escape"),
            ("logging", "path", "payments", "logs", "bad:colon.log"),
            ("logging", "path", "payments", "logs", "con.log"),
        ):
            r_bad_new = subprocess.run(
                [sys.executable, "-B", str(BIN / "astack-tools"), *bad_new],
                capture_output=True, text=True, env=env,
            )
            self.assertEqual(r_bad_new.returncode, 2, f"expected exit 2 for {bad_new}")


if __name__ == "__main__":
    unittest.main()
