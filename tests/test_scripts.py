"""Behaviour tests for astack's scripts: what a lead or a hook sees when it runs them."""
import json
import os
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


if __name__ == "__main__":
    unittest.main()
