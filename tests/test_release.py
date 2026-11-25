"""Behavioral tests for bin/astack-release: multi-repo sequencing, output handoffs, PR sync, autonomy gates, and rollback plans."""
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "bin" / "astack-release"


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-B", str(BIN), *args],
        capture_output=True,
        text=True,
    )


class ReleaseTrainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="astack-release-test-")
        self.dir = Path(self.tmp.name)
        self.state = self.dir / "release.json"
        self.md = self.dir / "RELEASE.md"
        self.settings = self.dir / "settings.json"
        self.settings.write_text(json.dumps({
            "autonomy": {
                "mode": "unattended",
                "allow": ["open_and_update_pr", "watch_pr_and_fix_ci"],
                "deny": ["merge_pr", "prod_deploy_or_destructive_migration"],
            }
        }))

    def tearDown(self):
        self.tmp.cleanup()

    def test_multi_repo_roles_security_app_sequence_with_outputs_pr_sync_and_rollback(self):
        """End-to-end roles -> security repo -> app repo sequence with PR sync, output interpolation, and reverse rollback."""
        spec = {
            "name": "rds-iam-cutover",
            "goal": "Switch app from RDS password to IAM auth across infra-iam, security-repo, and app-repo without outage.",
            "steps": [
                {
                    "id": "iam-roles-pr",
                    "kind": "pr",
                    "phase": "expand",
                    "repo": "infra-iam",
                    "title": "Create app and migrator IAM roles",
                    "pr_url": "https://github.com/org/infra-iam/pull/10",
                    "rollback_cmd": "git revert <iam-roles-pr>",
                },
                {
                    "id": "iam-roles-apply",
                    "kind": "deploy",
                    "phase": "expand",
                    "repo": "infra-iam",
                    "env": "prod",
                    "title": "Apply IAM roles at {{iam-roles-pr.merge_sha}}",
                    "depends_on": ["iam-roles-pr"],
                    "requires_outputs": ["iam-roles-pr.merge_sha"],
                    "plan_cmd": "terraform plan -out=iam.plan",
                    "verify_cmd": "true",
                    "rollback_cmd": "terraform apply -target=module.iam prev.plan",
                },
                {
                    "id": "security-pr",
                    "kind": "pr",
                    "phase": "expand",
                    "repo": "security-repo",
                    "title": "Grant KMS and RDS policy to {{iam-roles-apply.app_role_arn}}",
                    "depends_on": ["iam-roles-apply"],
                    "requires_outputs": ["iam-roles-apply.app_role_arn", "iam-roles-apply.migrator_role_arn"],
                    "rollback_cmd": "git revert <security-pr>",
                },
                {
                    "id": "app-cutover-pr",
                    "kind": "pr",
                    "phase": "switch",
                    "repo": "app-repo",
                    "title": "Switch app to {{iam-roles-apply.app_role_arn}} and {{security-pr.policy_tag}}",
                    "depends_on": ["iam-roles-apply", "security-pr"],
                    "requires_outputs": ["iam-roles-apply.app_role_arn", "security-pr.policy_tag"],
                    "rollback_cmd": "helm rollback app-service",
                },
                {
                    "id": "verify-zero-legacy",
                    "kind": "verify",
                    "phase": "switch",
                    "repo": "app-repo",
                    "env": "prod",
                    "title": "Confirm zero legacy password sessions",
                    "depends_on": ["app-cutover-pr"],
                    "verify_cmd": "echo zero-legacy-ok",
                },
                {
                    "id": "retire-legacy-pr",
                    "kind": "pr",
                    "phase": "contract",
                    "repo": "app-repo",
                    "title": "Drop legacy password grants",
                    "depends_on": ["verify-zero-legacy"],
                },
            ],
        }
        spec_path = self.dir / "spec.json"
        spec_path.write_text(json.dumps(spec))

        # Load spec & verify only iam-roles-pr is ready
        res = run_cli("load", str(self.state), "--spec", str(spec_path), "--markdown", str(self.md))
        self.assertEqual(res.returncode, 0, res.stderr)
        ready = json.loads(run_cli("ready", str(self.state), "--settings", str(self.settings), "--json").stdout)
        self.assertEqual([s["id"] for s in ready["ready"]], ["iam-roles-pr"])

        # Cannot jump ahead to blocked downstream step
        bad = run_cli("start", str(self.state), "--id", "security-pr", "--settings", str(self.settings))
        self.assertEqual(bad.returncode, 2)
        self.assertIn("blocked", bad.stderr)

        # Fake PR watcher: first returns merge_ready (parks in waiting_human due to autonomy.deny: merge_pr), then merged
        watcher_state = self.dir / "watcher_state.json"
        fake_watcher = self.dir / "fake-watch-pr"
        fake_watcher.write_text(
            "#!/usr/bin/env python3\n"
            "import json, sys\n"
            f"data = json.loads(open({str(watcher_state)!r}).read())\n"
            "print(json.dumps(data[sys.argv[1]]))\n"
        )
        fake_watcher.chmod(0o755)

        watcher_state.write_text(json.dumps({
            "https://github.com/org/infra-iam/pull/10": {
                "state": "merge_ready",
                "snapshot": {"head_sha": "abc1234"},
            }
        }))
        sync1 = json.loads(run_cli(
            "sync", str(self.state), "--settings", str(self.settings),
            "--pr-watcher", str(fake_watcher), "--json"
        ).stdout)
        self.assertEqual(sync1["synced"][0]["to_status"], "waiting_human")
        self.assertEqual(sync1["ready"], [])

        # Human merges PR -> sync unlocks iam-roles-apply with merge_sha output
        watcher_state.write_text(json.dumps({
            "https://github.com/org/infra-iam/pull/10": {
                "state": "merged",
                "snapshot": {"head_sha": "abc1234", "merge_commit_sha": "deadbeef"},
            }
        }))
        sync2 = json.loads(run_cli(
            "sync", str(self.state), "--settings", str(self.settings),
            "--pr-watcher", str(fake_watcher), "--json"
        ).stdout)
        self.assertEqual(sync2["synced"][0]["to_status"], "done")
        self.assertEqual(sync2["ready"], ["iam-roles-apply"])

        # Starting prod deploy parks in waiting_human due to autonomy.deny
        start_deploy = json.loads(run_cli(
            "start", str(self.state), "--id", "iam-roles-apply",
            "--settings", str(self.settings), "--json"
        ).stdout)
        self.assertEqual(start_deploy["status"], "waiting_human")
        self.assertIn("deadbeef", start_deploy["title"])

        # Completing iam-roles-apply with role ARNs unlocks security-pr AND interpolates inputs
        comp = json.loads(run_cli(
            "complete", str(self.state), "--id", "iam-roles-apply",
            "--output", "app_role_arn=arn:aws:iam::123456789012:role/app",
            "--output", "migrator_role_arn=arn:aws:iam::123456789012:role/migrator",
            "--settings", str(self.settings), "--json"
        ).stdout)
        self.assertEqual(comp["ready"], ["security-pr"])

        ready_sec = json.loads(run_cli("ready", str(self.state), "--settings", str(self.settings), "--json").stdout)
        sec_item = ready_sec["ready"][0]
        self.assertEqual(sec_item["inputs"]["iam-roles-apply.app_role_arn"], "arn:aws:iam::123456789012:role/app")
        self.assertIn("arn:aws:iam::123456789012:role/app", sec_item["title"])

        # Complete security-pr with policy_tag -> unlocks app-cutover-pr with BOTH upstream outputs!
        run_cli("set-pr", str(self.state), "--id", "security-pr", "--pr-url", "https://github.com/org/security-repo/pull/22")
        comp_sec = json.loads(run_cli(
            "complete", str(self.state), "--id", "security-pr",
            "--output", "policy_tag=sec-v2.1.0",
            "--settings", str(self.settings), "--json"
        ).stdout)
        self.assertEqual(comp_sec["ready"], ["app-cutover-pr"])

        ready_app = json.loads(run_cli("ready", str(self.state), "--settings", str(self.settings), "--json").stdout)
        app_item = ready_app["ready"][0]
        self.assertEqual(app_item["inputs"]["iam-roles-apply.app_role_arn"], "arn:aws:iam::123456789012:role/app")
        self.assertEqual(app_item["inputs"]["security-pr.policy_tag"], "sec-v2.1.0")
        self.assertIn("sec-v2.1.0", app_item["title"])

        # Complete app-cutover-pr, then run verify --run on verify-zero-legacy -> unlocks retire-legacy-pr
        run_cli("complete", str(self.state), "--id", "app-cutover-pr", "--settings", str(self.settings))
        ver = run_cli("verify", str(self.state), "--id", "verify-zero-legacy", "--run", "--settings", str(self.settings), "--json")
        self.assertEqual(ver.returncode, 0, ver.stderr)
        self.assertEqual(json.loads(ver.stdout)["step"]["status"], "done")

        # Fail retire-legacy-pr and verify reverse-topological rollback order (downstream before upstream!)
        failed = json.loads(run_cli(
            "fail", str(self.state), "--id", "retire-legacy-pr",
            "--reason", "rollback test", "--markdown", str(self.md), "--json"
        ).stdout)
        rb_ids = [s["id"] for s in failed["rollback_plan"]]
        self.assertLess(rb_ids.index("app-cutover-pr"), rb_ids.index("security-pr"))
        self.assertLess(rb_ids.index("security-pr"), rb_ids.index("iam-roles-apply"))
        self.assertLess(rb_ids.index("iam-roles-apply"), rb_ids.index("iam-roles-pr"))

        # Rendered Markdown includes Mermaid flowchart, phases, outputs, and rollback plan
        md_text = self.md.read_text()
        self.assertIn("```mermaid", md_text)
        self.assertIn("flowchart LR", md_text)
        self.assertIn("Phase 1: Expand", md_text)
        self.assertIn("Phase 2: Switch & Verify", md_text)
        self.assertIn("Phase 3: Contract", md_text)
        self.assertIn("iam-roles-apply.app_role_arn", md_text)
        self.assertIn("Reverse-Order Rollback Plan", md_text)

    def test_rejects_cycles_invalid_output_refs_and_secret_leaks(self):
        # Cycle rejection
        bad_cycle = self.dir / "cycle.json"
        bad_cycle.write_text(json.dumps({
            "name": "bad",
            "steps": [
                {"id": "a", "kind": "pr", "title": "A", "depends_on": ["b"]},
                {"id": "b", "kind": "pr", "title": "B", "depends_on": ["a"]},
            ],
        }))
        res = run_cli("load", str(self.state), "--spec", str(bad_cycle))
        self.assertEqual(res.returncode, 2)
        self.assertIn("cycle", res.stderr.lower())

        # Reject output reference to non-ancestor step
        bad_ref = self.dir / "bad_ref.json"
        bad_ref.write_text(json.dumps({
            "name": "bad-ref",
            "steps": [
                {"id": "a", "kind": "pr", "title": "A"},
                {"id": "b", "kind": "pr", "title": "B uses {{a.sha}}"},
            ],
        }))
        res2 = run_cli("load", str(self.state), "--spec", str(bad_ref))
        self.assertEqual(res2.returncode, 2)
        self.assertIn("not an upstream dependency", res2.stderr)

        # Reject raw secret stored in outputs (no-leaked-secrets)
        run_cli("init", str(self.state), "--name", "secret-test")
        run_cli("add-step", str(self.state), "--id", "s1", "--kind", "deploy", "--title", "Deploy")
        res3 = run_cli("complete", str(self.state), "--id", "s1", "--output", "token=ghp_1234567890abcdefghijklmno")
        self.assertEqual(res3.returncode, 2)
        self.assertIn("secret-like", res3.stderr)

    def test_pr_hold_and_post_merge_external_verification_gate_block_downstream_pr(self):
        """A dependency PR with verify_cmd stays in verifying after merge until external verification passes, holding downstream PRs."""
        flag = self.dir / "tf-applied.ok"
        spec = {
            "name": "dag-external-guard",
            "steps": [
                {
                    "id": "repo-a-pr",
                    "kind": "pr",
                    "phase": "expand",
                    "repo": "infra-roles",
                    "title": "Create IAM role in Repo A",
                    "pr_url": "https://github.com/org/infra-roles/pull/1",
                    "verify_cmd": f"test -f {flag}",
                },
                {
                    "id": "repo-b-pr",
                    "kind": "pr",
                    "phase": "switch",
                    "repo": "security-repo",
                    "title": "Reference Repo A role from {{repo-a-pr.merge_sha}}",
                    "depends_on": ["repo-a-pr"],
                    "requires_outputs": ["repo-a-pr.merge_sha"],
                    "pr_url": "https://github.com/org/security-repo/pull/2",
                    "gate_cmds": ["echo checking {{repo-a-pr.merge_sha}}"],
                },
            ],
        }
        spec_path = self.dir / "dag_spec.json"
        spec_path.write_text(json.dumps(spec))
        self.assertEqual(run_cli("load", str(self.state), "--spec", str(spec_path)).returncode, 0)

        # Fake watcher using the REAL astack-watch-pr `snapshots` list envelope
        watcher_state = self.dir / "w_state.json"
        fake_watcher = self.dir / "fake-watch"
        fake_watcher.write_text(
            "#!/usr/bin/env python3\n"
            "import json, sys\n"
            f"data = json.loads(open({str(watcher_state)!r}).read())\n"
            "print(json.dumps(data[sys.argv[1]]))\n"
        )
        fake_watcher.chmod(0o755)

        # 1. Repo A PR held -> stays in_progress (NOT waiting_human / NOT done)
        watcher_state.write_text(json.dumps({
            "https://github.com/org/infra-roles/pull/1": {
                "state": "held",
                "frontier": {"number": 1},
                "snapshots": [{"target": {"number": 1}, "head_sha": "aaa1111"}],
            },
            "https://github.com/org/security-repo/pull/2": {
                "state": "merge_ready",
                "frontier": {"number": 2},
                "snapshots": [{"target": {"number": 2}, "head_sha": "bbb2222"}],
            },
        }))
        s1 = json.loads(run_cli(
            "sync", str(self.state), "--settings", str(self.settings),
            "--pr-watcher", str(fake_watcher), "--json",
        ).stdout)
        self.assertEqual(s1["synced"][0]["to_status"], "in_progress")
        self.assertEqual(s1["ready"], [])

        # Explicitly syncing blocked Repo B PR even if forge says merge_ready MUST keep it held/pending!
        s_blocked = json.loads(run_cli(
            "sync", str(self.state), "--step", "repo-b-pr", "--settings", str(self.settings),
            "--pr-watcher", str(fake_watcher), "--json",
        ).stdout)
        self.assertEqual(s_blocked["synced"][0]["to_status"], "pending")

        # 2. Repo A PR merges -> because verify_cmd is set, it transitions to `verifying` (NOT `done`), keeping Repo B blocked!
        watcher_state.write_text(json.dumps({
            "https://github.com/org/infra-roles/pull/1": {
                "state": "merged",
                "frontier": {"number": 1},
                "snapshots": [{"target": {"number": 1}, "head_sha": "aaa1111"}],
            },
            "https://github.com/org/security-repo/pull/2": {
                "state": "merge_ready",
                "frontier": {"number": 2},
                "snapshots": [{"target": {"number": 2}, "head_sha": "bbb2222"}],
            },
        }))
        s2 = json.loads(run_cli(
            "sync", str(self.state), "--settings", str(self.settings),
            "--pr-watcher", str(fake_watcher), "--json",
        ).stdout)
        self.assertEqual(s2["synced"][0]["to_status"], "verifying")
        self.assertEqual(s2["synced"][0]["outputs"]["merge_sha"], "aaa1111")
        self.assertEqual(s2["ready"], [])  # Repo B STILL blocked until external Terraform apply verifies!

        # Verify fails before flag exists -> Repo B still blocked
        v_fail = run_cli("verify", str(self.state), "--id", "repo-a-pr", "--run", "--settings", str(self.settings), "--json")
        self.assertEqual(v_fail.returncode, 1)
        self.assertEqual(json.loads(v_fail.stdout)["step"]["status"], "failed")

        # 3. External Terraform apply finishes -> verify --run passes -> Repo A becomes done -> Repo B unlocks with interpolated gate_cmds!
        flag.write_text("applied")
        v_ok = run_cli("verify", str(self.state), "--id", "repo-a-pr", "--run", "--settings", str(self.settings), "--json")
        self.assertEqual(v_ok.returncode, 0, v_ok.stderr)
        self.assertEqual(json.loads(v_ok.stdout)["step"]["status"], "done")

        ready_b = json.loads(run_cli("ready", str(self.state), "--settings", str(self.settings), "--json").stdout)
        self.assertEqual([s["id"] for s in ready_b["ready"]], ["repo-b-pr"])
        self.assertEqual(ready_b["ready"][0]["gate_cmds"], ["echo checking aaa1111"])

        # Reject gate_cmd referencing non-ancestor output
        bad_gate = self.dir / "bad_gate.json"
        bad_gate.write_text(json.dumps({
            "name": "bad-gate",
            "steps": [
                {"id": "a", "kind": "pr", "title": "A"},
                {"id": "b", "kind": "pr", "title": "B", "gate_cmds": ["check {{a.sha}}"]},
            ],
        }))
        bad_res = run_cli("load", str(self.dir / "bad_gate_state.json"), "--spec", str(bad_gate))
        self.assertEqual(bad_res.returncode, 2)
        self.assertIn("not an upstream dependency", bad_res.stderr)


if __name__ == "__main__":
    unittest.main()
