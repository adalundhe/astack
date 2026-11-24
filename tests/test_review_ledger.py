"""Behaviour tests for bin/astack-review-ledger using hand-worked expected values."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent / "bin" / "astack-review-ledger"

POOL_3 = [
    {"provider": "anthropic", "model": "claude-opus-4-6", "effort": "high"},
    {"provider": "openai", "model": "gpt-5.4", "effort": "high"},
    {"provider": "google", "model": "gemini-2.5-pro", "effort": "high"},
]

POOL_2 = POOL_3[:2]
POOL_1 = POOL_3[:1]


def run_ledger(payload, *extra_args):
    proc = subprocess.run(
        [sys.executable, str(BIN), "-", *extra_args],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    return proc


def eval_json(payload):
    proc = run_ledger(payload, "--json")
    if proc.returncode != 0:
        raise AssertionError(f"unexpected exit {proc.returncode}: {proc.stderr}")
    return json.loads(proc.stdout)


def rcs(prefix, count):
    return [f"{prefix}-{i}" for i in range(1, count + 1)]


class ReviewLedgerTest(unittest.TestCase):
    def test_low_risk_one_reviewer_no_verified_bug_stops_clean(self):
        data = eval_json({
            "reviewer_pool": POOL_3,
            "vectors": [{"name": "cli-help", "risk": "low"}],
            "reviews": [
                {"vector": "cli-help", "provider": "anthropic", "model": "claude-opus-4-6", "verified": [], "dropped": 2}
            ],
        })
        vec = data["vectors"][0]
        self.assertEqual(vec["action"], "stop")
        self.assertEqual(vec["reason"], "clean_single_review")
        self.assertEqual(vec["status"], "STOPPED (clean single review)")
        self.assertIsNone(vec["estimate"])
        self.assertEqual(data["overall"], "complete")

    def test_low_risk_one_reviewer_one_verified_bug_adds_second_model(self):
        data = eval_json({
            "reviewer_pool": POOL_3,
            "vectors": [{"name": "cli-help", "risk": "low"}],
            "reviews": [
                {"vector": "cli-help", "provider": "anthropic", "model": "claude-opus-4-6", "verified": ["rc-1"], "dropped": 0}
            ],
        })
        vec = data["vectors"][0]
        self.assertEqual(vec["action"], "continue")
        self.assertEqual(vec["reason"], "verified_bug_on_low_risk_vector")
        self.assertEqual(vec["next_models"][0]["model"], "gpt-5.4")
        self.assertEqual(data["overall"], "continue")

    def test_low_risk_clean_own_reviewer_but_external_verified_bug_adds_second_model(self):
        data = eval_json({
            "reviewer_pool": POOL_3,
            "vectors": [
                {"name": "cli-help", "risk": "low"},
                {"name": "auth", "risk": "risky"},
            ],
            "reviews": [
                {"vector": "cli-help", "provider": "anthropic", "model": "claude-opus-4-6", "verified": [], "dropped": 0},
                {
                    "vector": "auth",
                    "provider": "openai",
                    "model": "gpt-5.4",
                    "verified": [{"root_cause": "rc-cross-1", "vector": "cli-help"}],
                    "dropped": 0,
                },
            ],
        })
        by_name = {v["name"]: v for v in data["vectors"]}
        cli = by_name["cli-help"]
        self.assertEqual(cli["action"], "continue")
        self.assertEqual(cli["reason"], "external_verified_bug_on_low_risk_vector")
        self.assertEqual(cli["verified_root_causes"], ["rc-cross-1"])
        self.assertEqual(cli["next_models"][0]["model"], "gpt-5.4")

    def test_risky_vector_with_one_reviewer_never_stops_and_adds_second_model(self):
        data = eval_json({
            "reviewer_pool": POOL_3,
            "vectors": [{"name": "concurrency", "risk": "risky", "triggers": ["concurrency"]}],
            "reviews": [
                {"vector": "concurrency", "provider": "anthropic", "model": "claude-opus-4-6", "verified": [], "dropped": 0}
            ],
        })
        vec = data["vectors"][0]
        self.assertEqual(vec["action"], "continue")
        self.assertEqual(vec["reason"], "risky_vector_requires_second_model")
        self.assertEqual(vec["next_models"][0]["model"], "gpt-5.4")

    def test_chapman_n1_6_n2_5_m_3_continues_with_N_9_5_unfound_1_5(self):
        shared = rcs("shared", 3)
        only1 = rcs("only1", 3)
        only2 = rcs("only2", 2)
        data = eval_json({
            "reviewer_pool": POOL_3,
            "vectors": [{"name": "persistence", "risk": "risky"}],
            "reviews": [
                {"vector": "persistence", "provider": "anthropic", "model": "claude-opus-4-6", "verified": shared + only1, "dropped": 1},
                {"vector": "persistence", "provider": "openai", "model": "gpt-5.4", "verified": shared + only2, "dropped": 0},
            ],
        })
        vec = data["vectors"][0]
        self.assertEqual(vec["action"], "continue")
        self.assertEqual(vec["estimate"]["n1"], 6)
        self.assertEqual(vec["estimate"]["n2"], 5)
        self.assertEqual(vec["estimate"]["m"], 3)
        self.assertAlmostEqual(vec["estimate"]["estimated_total"], 9.5)
        self.assertAlmostEqual(vec["estimate"]["estimated_unfound"], 1.5)
        self.assertTrue(vec["estimate"]["informative"])
        self.assertEqual(vec["next_models"][0]["model"], "gemini-2.5-pro")

    def test_chapman_n1_8_n2_6_m_5_stops_with_N_9_5_unfound_0_5(self):
        # Exercises incremental union too: reviewer 1 (5) + reviewer 2 (3 new) -> n1=8; reviewer 3 finds 5 shared + 1 new -> n2=6, m=5
        r1 = rcs("rc", 5)
        r2 = ["rc-6", "rc-7", "rc-8"]
        r3 = ["rc-1", "rc-2", "rc-3", "rc-4", "rc-6", "rc-9"]
        data = eval_json({
            "reviewer_pool": POOL_3,
            "vectors": [{"name": "persistence", "risk": "risky"}],
            "reviews": [
                {"vector": "persistence", "provider": "anthropic", "model": "claude-opus-4-6", "verified": r1, "dropped": 0},
                {"vector": "persistence", "provider": "openai", "model": "gpt-5.4", "verified": r2, "dropped": 0},
                {"vector": "persistence", "provider": "google", "model": "gemini-2.5-pro", "verified": r3, "dropped": 0},
            ],
        })
        vec = data["vectors"][0]
        self.assertEqual(vec["action"], "stop")
        self.assertEqual(vec["status"], "STOPPED (estimate)")
        self.assertEqual(vec["estimate"]["n1"], 8)
        self.assertEqual(vec["estimate"]["n2"], 6)
        self.assertEqual(vec["estimate"]["m"], 5)
        self.assertAlmostEqual(vec["estimate"]["estimated_total"], 9.5)
        self.assertAlmostEqual(vec["estimate"]["estimated_unfound"], 0.5)
        self.assertTrue(vec["estimate"]["informative"])

    def test_chapman_n1_6_n2_4_m_4_stops_nothing_new(self):
        r1 = rcs("rc", 6)
        r2 = r1[:4]
        data = eval_json({
            "reviewer_pool": POOL_3,
            "vectors": [{"name": "auth", "risk": "risky"}],
            "reviews": [
                {"vector": "auth", "provider": "anthropic", "model": "claude-opus-4-6", "verified": r1, "dropped": 0},
                {"vector": "auth", "provider": "openai", "model": "gpt-5.4", "verified": r2, "dropped": 0},
            ],
        })
        vec = data["vectors"][0]
        self.assertEqual(vec["action"], "stop")
        self.assertEqual(vec["estimate"]["n1"], 6)
        self.assertEqual(vec["estimate"]["n2"], 4)
        self.assertEqual(vec["estimate"]["m"], 4)
        self.assertAlmostEqual(vec["estimate"]["estimated_total"], 6.0)
        self.assertAlmostEqual(vec["estimate"]["estimated_unfound"], 0.0)
        self.assertTrue(vec["estimate"]["informative"])

    def test_chapman_n1_3_n2_2_m_0_continues_with_N_11_unfound_6(self):
        data = eval_json({
            "reviewer_pool": POOL_3,
            "vectors": [{"name": "seams", "risk": "risky"}],
            "reviews": [
                {"vector": "seams", "provider": "anthropic", "model": "claude-opus-4-6", "verified": rcs("a", 3), "dropped": 0},
                {"vector": "seams", "provider": "openai", "model": "gpt-5.4", "verified": rcs("b", 2), "dropped": 0},
            ],
        })
        vec = data["vectors"][0]
        self.assertEqual(vec["action"], "continue")
        self.assertEqual(vec["estimate"]["n1"], 3)
        self.assertEqual(vec["estimate"]["n2"], 2)
        self.assertEqual(vec["estimate"]["m"], 0)
        self.assertAlmostEqual(vec["estimate"]["estimated_total"], 11.0)
        self.assertAlmostEqual(vec["estimate"]["estimated_unfound"], 6.0)
        self.assertFalse(vec["estimate"]["informative"])

    def test_chapman_n1_0_n2_0_m_0_stops_both_found_nothing(self):
        data = eval_json({
            "reviewer_pool": POOL_3,
            "vectors": [{"name": "concurrency", "risk": "risky"}],
            "reviews": [
                {"vector": "concurrency", "provider": "anthropic", "model": "claude-opus-4-6", "verified": [], "dropped": 1},
                {"vector": "concurrency", "provider": "openai", "model": "gpt-5.4", "verified": [], "dropped": 0},
            ],
        })
        vec = data["vectors"][0]
        self.assertEqual(vec["action"], "stop")
        self.assertEqual(vec["reason"], "both_found_nothing")
        self.assertEqual(vec["estimate"]["n1"], 0)
        self.assertEqual(vec["estimate"]["n2"], 0)
        self.assertEqual(vec["estimate"]["m"], 0)
        self.assertAlmostEqual(vec["estimate"]["estimated_total"], 0.0)
        self.assertAlmostEqual(vec["estimate"]["estimated_unfound"], 0.0)
        self.assertTrue(vec["estimate"]["informative"])

    def test_chapman_one_sided_zero_is_uninformative_and_continues(self):
        # Case A: n1=2, n2=0, m=0 -> unfound=0 by formula, but uninformative -> continue
        data_a = eval_json({
            "reviewer_pool": POOL_3,
            "vectors": [{"name": "auth", "risk": "risky"}],
            "reviews": [
                {"vector": "auth", "provider": "anthropic", "model": "claude-opus-4-6", "verified": rcs("a", 2), "dropped": 0},
                {"vector": "auth", "provider": "openai", "model": "gpt-5.4", "verified": [], "dropped": 0},
            ],
        })
        vec_a = data_a["vectors"][0]
        self.assertEqual(vec_a["action"], "continue")
        self.assertAlmostEqual(vec_a["estimate"]["estimated_total"], 2.0)
        self.assertAlmostEqual(vec_a["estimate"]["estimated_unfound"], 0.0)
        self.assertFalse(vec_a["estimate"]["informative"])

        # Case B: n1=0, n2=2, m=0 -> unfound=0 by formula, but uninformative -> continue
        data_b = eval_json({
            "reviewer_pool": POOL_3,
            "vectors": [{"name": "auth", "risk": "risky"}],
            "reviews": [
                {"vector": "auth", "provider": "anthropic", "model": "claude-opus-4-6", "verified": [], "dropped": 0},
                {"vector": "auth", "provider": "openai", "model": "gpt-5.4", "verified": rcs("b", 2), "dropped": 0},
            ],
        })
        vec_b = data_b["vectors"][0]
        self.assertEqual(vec_b["action"], "continue")
        self.assertAlmostEqual(vec_b["estimate"]["estimated_total"], 2.0)
        self.assertAlmostEqual(vec_b["estimate"]["estimated_unfound"], 0.0)
        self.assertFalse(vec_b["estimate"]["informative"])

    def test_pool_exhausted_while_vector_cannot_stop_flags_with_estimate(self):
        shared = rcs("s", 3)
        data = eval_json({
            "reviewer_pool": POOL_2,
            "vectors": [{"name": "concurrency", "risk": "risky"}],
            "reviews": [
                {"vector": "concurrency", "provider": "anthropic", "model": "claude-opus-4-6", "verified": shared + rcs("a", 3), "dropped": 1},
                {"vector": "concurrency", "provider": "openai", "model": "gpt-5.4", "verified": shared + rcs("b", 2), "dropped": 2},
            ],
        })
        vec = data["vectors"][0]
        self.assertEqual(vec["action"], "flag")
        self.assertEqual(vec["status"], "POOL EXHAUSTED")
        self.assertAlmostEqual(vec["estimate"]["estimated_total"], 9.5)
        self.assertAlmostEqual(vec["estimate"]["estimated_unfound"], 1.5)
        self.assertEqual(data["overall"], "flagged")
        self.assertEqual(len(data["pool_exhausted"]), 1)

    def test_single_model_pool_flags_any_vector_needing_second_model(self):
        data = eval_json({
            "reviewer_pool": POOL_1,
            "vectors": [
                {"name": "concurrency", "risk": "risky"},
                {"name": "cli-help", "risk": "low"},
                {"name": "clean-low", "risk": "low"},
            ],
            "reviews": [
                {"vector": "concurrency", "provider": "anthropic", "model": "claude-opus-4-6", "verified": [], "dropped": 0},
                {"vector": "cli-help", "provider": "anthropic", "model": "claude-opus-4-6", "verified": ["rc-1"], "dropped": 0},
                {"vector": "clean-low", "provider": "anthropic", "model": "claude-opus-4-6", "verified": [], "dropped": 0},
            ],
        })
        by_name = {v["name"]: v for v in data["vectors"]}
        self.assertEqual(by_name["concurrency"]["action"], "flag")
        self.assertEqual(by_name["concurrency"]["status"], "POOL EXHAUSTED")
        self.assertEqual(by_name["cli-help"]["action"], "flag")
        self.assertEqual(by_name["cli-help"]["status"], "POOL EXHAUSTED")
        self.assertEqual(by_name["clean-low"]["action"], "stop")
        self.assertEqual(data["overall"], "flagged")
        self.assertEqual({x["vector"] for x in data["pool_exhausted"]}, {"concurrency", "cli-help"})

    def test_prefers_non_worker_model_and_renders_coverage_map_and_lanes_lines(self):
        payload = {
            "target": "lane/auth@deadbeef",
            "worker_model": {"provider": "anthropic", "model": "claude-opus-4-6", "effort": "high"},
            "reviewer_pool": POOL_2,
            "vectors": [
                {"name": "auth", "risk": "risky", "triggers": ["auth/security"]},
                {"name": "cli", "risk": "low"},
                {"name": "unassigned-vec", "risk": "low", "could_not_test": ["no live IDP sandbox"]},
            ],
            "reviews": [
                {"vector": "auth", "provider": "anthropic", "model": "claude-opus-4-6", "verified": ["rc-1", "rc-2"], "dropped": 1},
                {"vector": "cli", "provider": "openai", "model": "gpt-5.4", "verified": [], "dropped": 0},
            ],
        }
        data = eval_json(payload)
        by_name = {v["name"]: v for v in data["vectors"]}
        # Worker used claude-opus-4-6, so next recommended model on auth and unassigned-vec must be gpt-5.4
        self.assertEqual(by_name["auth"]["next_models"][0]["model"], "gpt-5.4")
        self.assertEqual(by_name["unassigned-vec"]["next_models"][0]["model"], "gpt-5.4")
        self.assertEqual(data["not_assigned"], ["unassigned-vec"])

        md = run_ledger(payload, "--markdown")
        self.assertEqual(md.returncode, 0, md.stderr)
        self.assertIn("## Coverage map (`lane/auth@deadbeef`)", md.stdout)
        self.assertIn("NOT ASSIGNED\n- unassigned-vec", md.stdout)
        self.assertIn("POOL EXHAUSTED\n- none", md.stdout)
        self.assertIn("COULD NOT TEST\n- unassigned-vec: no live IDP sandbox", md.stdout)

        lanes = run_ledger(payload, "--lanes")
        self.assertEqual(lanes.returncode, 0, lanes.stderr)
        self.assertIn("vector=auth risk=risky model=anthropic/claude-opus-4-6 verified=2 dropped=1", lanes.stdout)
        self.assertIn("vector=cli risk=low model=openai/gpt-5.4 verified=0 dropped=0", lanes.stdout)

    def test_boundary_validation_rejects_retired_or_unapproved_inputs_with_exit_two(self):
        # 1. Retired roles.reviewer rejected (yagni: no fallback)
        res_old = run_ledger({
            "roles": {"reviewer": {"provider": "anthropic", "model": "claude-opus-4-6"}},
            "reviewer_pool": POOL_1,
            "vectors": [{"name": "v", "risk": "low"}],
        })
        self.assertEqual(res_old.returncode, 2)

        # 2. Single-object reviewer_pool rejected (must be a list)
        res_obj = run_ledger({
            "reviewer_pool": {"provider": "anthropic", "model": "claude-opus-4-6"},
            "vectors": [{"name": "v", "risk": "low"}],
        })
        self.assertEqual(res_obj.returncode, 2)

        # 3. Unapproved model in reviews rejected
        res_unapproved = run_ledger({
            "reviewer_pool": POOL_1,
            "vectors": [{"name": "v", "risk": "low"}],
            "reviews": [{"vector": "v", "provider": "openai", "model": "gpt-5.4", "verified": [], "dropped": 0}],
        })
        self.assertEqual(res_unapproved.returncode, 2)

        # 4. Invalid risk rejected
        res_risk = run_ledger({
            "reviewer_pool": POOL_1,
            "vectors": [{"name": "v", "risk": "medium"}],
        })
        self.assertEqual(res_risk.returncode, 2)

        # 5. Unknown vector in cross-vector finding rejected
        res_vec = run_ledger({
            "reviewer_pool": POOL_1,
            "vectors": [{"name": "v", "risk": "low"}],
            "reviews": [
                {
                    "vector": "v",
                    "provider": "anthropic",
                    "model": "claude-opus-4-6",
                    "verified": [{"root_cause": "rc-1", "vector": "ghost"}],
                    "dropped": 0,
                }
            ],
        })
        self.assertEqual(res_vec.returncode, 2)


if __name__ == "__main__":
    unittest.main()
