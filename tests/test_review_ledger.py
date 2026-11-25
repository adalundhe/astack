"""Behaviour tests for bin/astack-review-ledger: blocking-only estimates, fix-equivalence overlap checks,
exact k=2 hypergeometric lower/upper bounds, k>=3 Burnham-Overton + Beta-Binomial M_h observable-class
saturation, empirical per-model catch-rate calibration (zero picked 0.5 constant), clean uncalibrated
risky sweeps (no false landing block on 2-4 model pools), provider diversity, unreachable models,
and boundary validation."""
import importlib.machinery
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent / "bin" / "astack-review-ledger"

POOL_4 = [
    {"provider": "anthropic", "model": "claude-opus-4-6", "effort": "high", "harness": "claude"},
    {"provider": "openai", "model": "gpt-5.4", "effort": "high", "harness": "codex"},
    {"provider": "google", "model": "gemini-2.5-pro", "effort": "high", "harness": "agy"},
    {"provider": "anthropic", "model": "claude-sonnet-4-6", "effort": "medium", "harness": "pi"},
]

POOL_5 = POOL_4 + [
    {"provider": "openai", "model": "o3", "effort": "high", "harness": "codex"},
]


def _load_ledger_module():
    loader = importlib.machinery.SourceFileLoader("astack_review_ledger_mod", str(BIN))
    spec = importlib.util.spec_from_loader("astack_review_ledger_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["astack_review_ledger_mod"] = mod
    loader.exec_module(mod)
    return mod


def run_ledger(payload, *extra_args):
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run(
        [sys.executable, "-B", str(BIN), "-", *extra_args],
        input=text,
        capture_output=True,
        text=True,
    )


def eval_json(payload, *extra_args):
    res = run_ledger(payload, "--json", *extra_args)
    assert res.returncode == 0, f"unexpected exit {res.returncode}: {res.stderr}"
    return json.loads(res.stdout)


def eq_checks(vector, rcs):
    """Build fix-verified equivalence checks for a collection of shared blocking root causes."""
    return [
        {
            "vector": vector,
            "root_cause": rc,
            "reproductions": [f"repro-{rc}-a.py", f"repro-{rc}-b.py"],
            "fix_verified": True,
            "evidence": f"minimal fix for {rc} makes both reproductions pass",
        }
        for rc in rcs
    ]


class ReviewLedgerTest(unittest.TestCase):
    def test_low_risk_clean_single_review_stops_even_with_minor_findings(self):
        data = eval_json({
            "worker_model": {"provider": "anthropic", "model": "claude-sonnet-4-6", "effort": "medium"},
            "reviewer_pool": POOL_4,
            "vectors": [{"name": "docs-cli", "risk": "low"}],
            "reviews": [
                {
                    "vector": "docs-cli",
                    "provider": "anthropic",
                    "model": "claude-opus-4-6",
                    "verified": [
                        {"root_cause": "nit-comment", "severity": "nit"},
                        {"root_cause": "sug-rename", "severity": "suggestion"},
                    ],
                    "minor": ["nit-spacing"],
                    "dropped": 1,
                },
            ],
        })
        vec = data["vectors"][0]
        self.assertEqual(vec["action"], "stop")
        self.assertEqual(vec["verdict"], "clean_low_risk")
        self.assertEqual(vec["reason"], "clean_single_review")
        self.assertEqual(vec["verified_count"], 0)
        self.assertEqual(vec["minor_count"], 3)
        self.assertEqual(vec["dropped_count"], 1)
        self.assertFalse(vec["landing_blocked"])

    def test_low_risk_clean_two_reviews_still_stops_cleanly(self):
        data = eval_json({
            "worker_model": POOL_4[3],
            "reviewer_pool": POOL_4,
            "vectors": [{"name": "docs-cli", "risk": "low"}],
            "reviews": [
                {"vector": "docs-cli", "provider": "anthropic", "model": "claude-sonnet-4-6", "verified": [], "dropped": 0},
                {"vector": "docs-cli", "provider": "anthropic", "model": "claude-opus-4-6", "verified": [], "dropped": 0},
            ],
        })
        vec = data["vectors"][0]
        self.assertEqual(vec["action"], "stop")
        self.assertEqual(vec["verdict"], "clean_low_risk")
        self.assertEqual(vec["reason"], "clean_low_risk_review")
        self.assertFalse(vec["landing_blocked"])

    def test_low_risk_one_blocking_bug_adds_second_model(self):
        data = eval_json({
            "reviewer_pool": POOL_4,
            "vectors": [{"name": "cli", "risk": "low"}],
            "reviews": [
                {"vector": "cli", "provider": "anthropic", "model": "claude-opus-4-6", "verified": ["rc-exit-code"], "dropped": 0},
            ],
        })
        vec = data["vectors"][0]
        self.assertEqual(vec["action"], "continue")
        self.assertEqual(vec["reason"], "verified_bug_on_low_risk_vector")
        self.assertEqual(vec["next_models"][0]["model"], "gpt-5.4")

    def test_low_risk_clean_own_reviewer_but_external_blocking_bug_adds_second_model(self):
        data = eval_json({
            "reviewer_pool": POOL_4,
            "vectors": [
                {"name": "cli", "risk": "low"},
                {"name": "persistence", "risk": "risky"},
            ],
            "reviews": [
                {"vector": "cli", "provider": "anthropic", "model": "claude-opus-4-6", "verified": [], "dropped": 0},
                {
                    "vector": "persistence",
                    "provider": "openai",
                    "model": "gpt-5.4",
                    "verified": [
                        {"root_cause": "rc-wal", "vector": "persistence", "severity": "blocking"},
                        {"root_cause": "rc-cli-flag", "vector": "cli", "severity": "blocking"},
                    ],
                    "dropped": 0,
                },
            ],
        })
        by_vec = {v["name"]: v for v in data["vectors"]}
        self.assertEqual(by_vec["cli"]["action"], "continue")
        self.assertEqual(by_vec["cli"]["reason"], "external_verified_bug_on_low_risk_vector")
        self.assertEqual(by_vec["cli"]["verified_root_causes"], ["rc-cli-flag"])

    def test_risky_vector_with_one_reviewer_never_stops_and_blocks_single_model_pool(self):
        data = eval_json({
            "reviewer_pool": POOL_4,
            "vectors": [{"name": "concurrency", "risk": "risky", "triggers": ["concurrency"]}],
            "reviews": [
                {"vector": "concurrency", "provider": "anthropic", "model": "claude-opus-4-6", "verified": [], "dropped": 0},
            ],
        })
        vec = data["vectors"][0]
        self.assertEqual(vec["action"], "continue")
        self.assertEqual(vec["reason"], "risky_vector_requires_second_model")

        # 1-model pool on risky vector MUST still block landing
        one_model = eval_json({
            "reviewer_pool": POOL_4[:1],
            "vectors": [{"name": "concurrency", "risk": "risky"}],
            "reviews": [
                {"vector": "concurrency", "provider": "anthropic", "model": "claude-opus-4-6", "verified": [], "dropped": 0},
            ],
        })
        self.assertEqual(one_model["vectors"][0]["action"], "flag")
        self.assertTrue(one_model["landing_blocked"])

    def test_uncalibrated_clean_risky_sweep_does_not_block_2_to_4_model_pools_and_enforces_provider_diversity(self):
        # Bug 2 fix: clean risky vectors with 2-4 uncalibrated models must NOT block landing 100% of the time,
        # and must NEVER invent a picked 0.5 catch rate or claim 95% proof!
        # 1) 4-model multi-provider pool, 2 distinct providers clean -> clears honestly without blocking
        clean_2_provs = eval_json({
            "reviewer_pool": POOL_4,
            "vectors": [{"name": "seams", "risk": "risky"}],
            "reviews": [
                {"vector": "seams", "provider": "anthropic", "model": "claude-opus-4-6", "verified": [], "minor": ["nit-1"], "dropped": 1},
                {"vector": "seams", "provider": "openai", "model": "gpt-5.4", "verified": [], "dropped": 0},
            ],
        })
        vec = clean_2_provs["vectors"][0]
        self.assertEqual(vec["action"], "stop")
        self.assertEqual(vec["verdict"], "clean_uncalibrated")
        self.assertEqual(vec["reason"], "clean_sweep_uncalibrated")
        self.assertFalse(vec["landing_blocked"])
        self.assertFalse(vec["estimate"]["calibrated"])
        self.assertIsNone(vec["estimate"]["zero_bug_miss_prob"])
        self.assertIsNone(vec["estimate"]["estimated_unfound_upper"])
        self.assertIn("not yet calibrated", vec["scope_note"])
        self.assertIn("not proof", vec["scope_note"])

        # 2) Same-provider pair while another provider exists in the pool -> asks for cross-provider diversity first!
        same_prov = eval_json({
            "reviewer_pool": POOL_4,
            "vectors": [{"name": "seams", "risk": "risky"}],
            "reviews": [
                {"vector": "seams", "provider": "anthropic", "model": "claude-opus-4-6", "verified": [], "dropped": 0},
                {"vector": "seams", "provider": "anthropic", "model": "claude-sonnet-4-6", "verified": [], "dropped": 0},
            ],
        })
        self.assertEqual(same_prov["vectors"][0]["action"], "continue")
        self.assertEqual(same_prov["vectors"][0]["reason"], "clean_review_needs_provider_diversity")
        self.assertNotEqual(same_prov["vectors"][0]["next_models"][0]["provider"], "anthropic")

        # 3) Single-provider 2-model pool (no other provider exists) -> clears cleanly without blocking landing
        single_prov_pool = [POOL_4[0], POOL_4[3]]
        clean_single_prov = eval_json({
            "reviewer_pool": single_prov_pool,
            "vectors": [{"name": "seams", "risk": "risky"}],
            "reviews": [
                {"vector": "seams", "provider": "anthropic", "model": "claude-opus-4-6", "verified": [], "dropped": 0},
                {"vector": "seams", "provider": "anthropic", "model": "claude-sonnet-4-6", "verified": [], "dropped": 0},
            ],
        })
        self.assertEqual(clean_single_prov["vectors"][0]["action"], "stop")
        self.assertEqual(clean_single_prov["vectors"][0]["verdict"], "clean_uncalibrated")
        self.assertFalse(clean_single_prov["landing_blocked"])

    def test_empirical_catch_rate_calibration_drives_clean_risky_stopping_without_picked_constants(self):
        # Strong calibrated models (5/5 each -> Jeffreys miss prob = 0.5/6 = 0.0833 -> 2 models = 0.0069 < 0.05) clear at k=2!
        cal_strong = {
            "anthropic/claude-opus-4-6": {"detected": 5, "planted": 5},
            "openai/gpt-5.4": {"detected": 5, "planted": 5},
        }
        strong = eval_json({
            "model_catch_rates": cal_strong,
            "reviewer_pool": POOL_4,
            "vectors": [{"name": "auth", "risk": "risky"}],
            "reviews": [
                {"vector": "auth", "provider": "anthropic", "model": "claude-opus-4-6", "verified": [], "dropped": 0},
                {"vector": "auth", "provider": "openai", "model": "gpt-5.4", "verified": [], "dropped": 0},
            ],
        })
        v_s = strong["vectors"][0]
        self.assertEqual(v_s["action"], "stop")
        self.assertEqual(v_s["verdict"], "clean_calibrated")
        self.assertEqual(v_s["reason"], "clean_calibrated_review")
        self.assertFalse(v_s["landing_blocked"])
        self.assertTrue(v_s["estimate"]["calibrated"])
        self.assertLess(v_s["estimate"]["zero_bug_miss_prob"], 0.05)
        self.assertIn("harder bugs or shared blind spots", v_s["scope_note"])

        # Moderate calibrated models (3/5 each -> Jeffreys miss prob = 2.5/6 = 0.4167):
        # k=2 (0.1736) continues, k=3 (0.0723) continues, k=4 (0.0301 < 0.05) clears!
        cal_mod = {
            f"{m['provider']}/{m['model']}": {"detected": 3, "planted": 5}
            for m in POOL_4
        }
        with tempfile.TemporaryDirectory(prefix="astack-cal-test-") as td:
            cal_file = Path(td) / "calibration.json"
            cal_file.write_text(json.dumps({"schema_version": "1.0", "models": cal_mod}))
            for k, expected_action in ((2, "continue"), (3, "continue"), (4, "stop")):
                res = eval_json(
                    {
                        "reviewer_pool": POOL_4,
                        "vectors": [{"name": "auth", "risk": "risky"}],
                        "reviews": [
                            {"vector": "auth", "provider": POOL_4[i]["provider"], "model": POOL_4[i]["model"], "verified": [], "dropped": 0}
                            for i in range(k)
                        ],
                    },
                    "--calibration",
                    str(cal_file),
                )
                self.assertEqual(res["vectors"][0]["action"], expected_action, f"unexpected action at k={k}")

        # Weak calibrated 2-model pool (1/5 each -> 0.75^2 = 0.5625 >= 0.05) -> flags landing_blocked with measured 56% risk!
        weak = eval_json({
            "reviewer_pool": [
                {**POOL_4[0], "catch_rate": {"detected": 1, "planted": 5}},
                {**POOL_4[1], "catch_rate": {"detected": 1, "planted": 5}},
            ],
            "vectors": [{"name": "auth", "risk": "risky"}],
            "reviews": [
                {"vector": "auth", "provider": "anthropic", "model": "claude-opus-4-6", "verified": [], "dropped": 0},
                {"vector": "auth", "provider": "openai", "model": "gpt-5.4", "verified": [], "dropped": 0},
            ],
        })
        self.assertEqual(weak["vectors"][0]["action"], "flag")
        self.assertTrue(weak["landing_blocked"])
        self.assertIn("56% chance", weak["person_decisions"][0]["question"])

    def test_k2_cautious_upper_bound_refuses_premature_stop_on_small_counts(self):
        shared = [f"s{i}" for i in range(5)]
        r1 = shared + ["a1", "a2", "a3"]
        r2 = shared + ["b1"]
        data = eval_json({
            "reviewer_pool": POOL_4,
            "vectors": [{"name": "auth", "risk": "risky"}],
            "equivalence_checks": eq_checks("auth", shared),
            "reviews": [
                {"vector": "auth", "provider": "anthropic", "model": "claude-opus-4-6", "verified": r1, "dropped": 0},
                {"vector": "auth", "provider": "openai", "model": "gpt-5.4", "verified": r2, "dropped": 0},
            ],
        })
        vec = data["vectors"][0]
        self.assertEqual(vec["action"], "continue")
        self.assertEqual(vec["reason"], "models_still_finding_new_bugs")
        est = vec["estimate"]
        self.assertEqual(est["estimator"], "chapman_hypergeometric_95")
        self.assertAlmostEqual(est["estimated_unfound"], 0.5)
        self.assertGreaterEqual(est["estimated_unfound_upper"], 5.0)
        self.assertEqual(vec["next_models"][0]["model"], "gemini-2.5-pro")

    def test_k2_exact_hypergeometric_lower_and_upper_bounds(self):
        # Case 1: n1=6, n2=6, m=1 (D=11) -> exact lower_N = 13 (unfound_lower = 2), exact upper_N = 707 (unfound_upper = 696).
        r1 = ["s0", "a1", "a2", "a3", "a4", "a5"]
        r2 = ["s0", "b1", "b2", "b3", "b4", "b5"]
        data_m1 = eval_json({
            "reviewer_pool": POOL_4[:2],
            "vectors": [{"name": "auth", "risk": "risky"}],
            "equivalence_checks": eq_checks("auth", ["s0"]),
            "reviews": [
                {"vector": "auth", "provider": "anthropic", "model": "claude-opus-4-6", "verified": r1, "dropped": 0},
                {"vector": "auth", "provider": "openai", "model": "gpt-5.4", "verified": r2, "dropped": 0},
            ],
        })
        est_m1 = data_m1["vectors"][0]["estimate"]
        self.assertEqual(est_m1["estimated_unfound_lower"], 2.0)
        self.assertEqual(est_m1["estimated_unfound_upper"], 696.0)
        self.assertEqual(data_m1["person_decisions"][0]["estimated_remaining_range"], [2.0, 696.0])
        self.assertIn("range 2–696", data_m1["person_decisions"][0]["question"])

        # Case 2: n1=4, n2=4, m=0 (D=8) -> exact lower_N = 10 (unfound_lower = 2), upper is unbounded (None).
        data_m0 = eval_json({
            "reviewer_pool": POOL_4[:2],
            "vectors": [{"name": "persistence", "risk": "risky"}],
            "reviews": [
                {"vector": "persistence", "provider": "anthropic", "model": "claude-opus-4-6", "verified": ["a1", "a2", "a3", "a4"], "dropped": 0},
                {"vector": "persistence", "provider": "openai", "model": "gpt-5.4", "verified": ["b1", "b2", "b3", "b4"], "dropped": 0},
            ],
        })
        est_m0 = data_m0["vectors"][0]["estimate"]
        self.assertEqual(est_m0["estimated_unfound_lower"], 2.0)
        self.assertIsNone(est_m0["estimated_unfound_upper"])
        self.assertIn("at least 2", data_m0["person_decisions"][0]["question"])

        # Case 3: n1=10, n2=10, m=2 (D=18) -> exact lower_N = 23 (unfound_lower = 5), exact upper_N = 262 (unfound_upper = 244).
        shared2 = ["s0", "s1"]
        data_m2 = eval_json({
            "reviewer_pool": POOL_4,
            "vectors": [{"name": "core", "risk": "risky"}],
            "equivalence_checks": eq_checks("core", shared2),
            "reviews": [
                {"vector": "core", "provider": "anthropic", "model": "claude-opus-4-6", "verified": shared2 + [f"a{i}" for i in range(8)], "dropped": 0},
                {"vector": "core", "provider": "openai", "model": "gpt-5.4", "verified": shared2 + [f"b{i}" for i in range(8)], "dropped": 0},
            ],
        })
        est_m2 = data_m2["vectors"][0]["estimate"]
        self.assertEqual(est_m2["estimated_unfound_lower"], 5.0)
        self.assertEqual(est_m2["estimated_unfound_upper"], 244.0)

    def test_k2_large_complete_overlap_saturates(self):
        shared = [f"rc-{i}" for i in range(20)]
        data = eval_json({
            "reviewer_pool": POOL_4,
            "vectors": [{"name": "core", "risk": "risky"}],
            "equivalence_checks": eq_checks("core", shared),
            "reviews": [
                {"vector": "core", "provider": "anthropic", "model": "claude-opus-4-6", "verified": shared, "dropped": 0},
                {"vector": "core", "provider": "openai", "model": "gpt-5.4", "verified": shared, "dropped": 0},
            ],
        })
        vec = data["vectors"][0]
        self.assertEqual(vec["action"], "stop")
        self.assertEqual(vec["verdict"], "saturated")
        self.assertEqual(vec["status"], "STOPPED (saturated)")
        self.assertIn("stopped finding new blocking bugs", vec["scope_note"])
        self.assertEqual(vec["estimate"]["estimated_unfound_lower"], 0.0)
        self.assertEqual(vec["estimate"]["estimated_unfound_upper"], 0.0)

    def test_k2_zero_overlap_is_uninformative_and_unbounded(self):
        data = eval_json({
            "reviewer_pool": POOL_4,
            "vectors": [{"name": "persistence", "risk": "risky"}],
            "reviews": [
                {"vector": "persistence", "provider": "anthropic", "model": "claude-opus-4-6", "verified": ["a1", "a2"], "dropped": 0},
                {"vector": "persistence", "provider": "openai", "model": "gpt-5.4", "verified": ["b1"], "dropped": 0},
            ],
        })
        vec = data["vectors"][0]
        self.assertEqual(vec["action"], "continue")
        self.assertEqual(vec["reason"], "uninformative_no_verified_overlap")
        self.assertIsNone(vec["estimate"]["estimated_unfound_upper"])

    def test_unverified_overlap_merge_is_rejected_and_split(self):
        shared = ["rc-1", "rc-2"]
        data = eval_json({
            "reviewer_pool": POOL_5,
            "vectors": [{"name": "auth", "risk": "risky"}],
            "reviews": [
                {"vector": "auth", "provider": POOL_5[i]["provider"], "model": POOL_5[i]["model"], "verified": shared, "dropped": 0}
                for i in range(3)
            ],
        })
        vec = data["vectors"][0]
        self.assertEqual(vec["action"], "continue")
        self.assertTrue(any("unverified_overlap_merge" in v for v in vec["rule_violations"]))
        self.assertEqual(vec["estimate"]["recaptured"], 0)
        self.assertFalse(vec["estimate"]["informative"])

        # Same reviews WITH fix_verified=False -> STILL rejected!
        data_false = eval_json({
            "reviewer_pool": POOL_5,
            "vectors": [{"name": "auth", "risk": "risky"}],
            "equivalence_checks": [
                {"vector": "auth", "root_cause": rc, "reproductions": [f"r-{rc}-1.py", f"r-{rc}-2.py"], "fix_verified": False}
                for rc in shared
            ],
            "reviews": [
                {"vector": "auth", "provider": POOL_5[i]["provider"], "model": POOL_5[i]["model"], "verified": shared, "dropped": 0}
                for i in range(3)
            ],
        })
        self.assertEqual(data_false["vectors"][0]["action"], "continue")

        # Once fix_verified=True proves both shared root causes across 3 reviewers -> freqs=[0,0,2] -> saturates!
        data_ok = eval_json({
            "reviewer_pool": POOL_5,
            "vectors": [{"name": "auth", "risk": "risky"}],
            "equivalence_checks": eq_checks("auth", shared),
            "reviews": [
                {"vector": "auth", "provider": POOL_5[i]["provider"], "model": POOL_5[i]["model"], "verified": shared, "dropped": 0}
                for i in range(3)
            ],
        })
        vec_ok = data_ok["vectors"][0]
        self.assertEqual(vec_ok["action"], "stop")
        self.assertEqual(vec_ok["verdict"], "saturated")
        self.assertEqual(vec_ok["estimate"]["frequencies"], [0, 0, 2])
        self.assertEqual(vec_ok["estimate"]["estimated_unfound_upper"], 0.0)

    def test_beta_binomial_prevents_f1_zero_collapse_and_fixes_d1_paradox(self):
        mod = _load_ledger_module()
        # Thin f1=0 patterns MUST still continue (no variance collapse!)
        for t, freqs in ((3, [0, 0, 1]), (3, [0, 1, 2]), (4, [0, 2, 1, 1]), (4, [0, 1, 2, 0]), (5, [0, 1, 1, 1, 1])):
            est = mod.jackknife_mh_estimate(freqs, t)
            self.assertFalse(est["can_stop"], f"should not saturate on thin f1=0 pattern t={t} freqs={freqs}")
            self.assertGreaterEqual(est["estimated_unfound_upper"], 1.0)

        # D=1 paradox fixed: 5/5 (and 6/6) reviewers all finding the single bug saturates cleanly!
        for t in (5, 6):
            est1 = mod.jackknife_mh_estimate([0] * (t - 1) + [1], t)
            self.assertTrue(est1["can_stop"], f"expected saturation at t={t} all-found D=1")
            self.assertEqual(est1["estimated_unfound_upper"], 0.0)

        # Monotone for large D consensus
        for D in (2, 5, 10, 20):
            est = mod.jackknife_mh_estimate([0, 0, 0, D], 4)
            self.assertTrue(est["can_stop"], f"expected saturation at t=4 freqs=[0,0,0,{D}]")
            self.assertEqual(est["estimated_unfound_upper"], 0.0)

    def test_run_out_pool_blocks_landing_on_risky_vector_with_range_and_plain_decision(self):
        pool_2 = POOL_4[:2]
        data = eval_json({
            "reviewer_pool": pool_2,
            "vectors": [
                {"name": "concurrency", "risk": "risky"},
                {"name": "formatting", "risk": "low"},
            ],
            "equivalence_checks": eq_checks("concurrency", ["rc-1"]),
            "reviews": [
                {"vector": "concurrency", "provider": "anthropic", "model": "claude-opus-4-6", "verified": ["rc-1", "rc-2"], "dropped": 0},
                {"vector": "concurrency", "provider": "openai", "model": "gpt-5.4", "verified": ["rc-1", "rc-3"], "dropped": 0},
                {"vector": "formatting", "provider": "anthropic", "model": "claude-opus-4-6", "verified": ["rc-fmt"], "dropped": 0},
                {"vector": "formatting", "provider": "openai", "model": "gpt-5.4", "verified": [], "dropped": 0},
            ],
        })
        self.assertEqual(data["overall"], "flagged")
        self.assertTrue(data["landing_blocked"])
        by_v = {v["name"]: v for v in data["vectors"]}
        self.assertTrue(by_v["concurrency"]["landing_blocked"])
        self.assertFalse(by_v["formatting"]["landing_blocked"])
        decision = data["person_decisions"][0]
        self.assertEqual(decision["area"], "concurrency")
        self.assertEqual(decision["proven_blocking"], 3)
        self.assertIn("similar detectability", decision["question"])
        self.assertIn("Approve additional reviewer models", decision["question"])
        self.assertNotIn("POOL EXHAUSTED", decision["question"])

    def test_planted_bugs_continue_through_k4_and_saturate_at_k5(self):
        step_k4 = eval_json({
            "worker_model": POOL_5[3],
            "reviewer_pool": POOL_5,
            "vectors": [{"name": "batch-and-persistence", "risk": "risky"}],
            "equivalence_checks": eq_checks("batch-and-persistence", ["rc-easy", "rc-med", "rc-hard"]),
            "reviews": [
                {"vector": "batch-and-persistence", "provider": POOL_5[0]["provider"], "model": POOL_5[0]["model"], "verified": ["rc-easy", "rc-med"], "dropped": 0},
                {"vector": "batch-and-persistence", "provider": POOL_5[1]["provider"], "model": POOL_5[1]["model"], "verified": ["rc-easy"], "minor": ["nit-comment"], "dropped": 0},
                {"vector": "batch-and-persistence", "provider": POOL_5[2]["provider"], "model": POOL_5[2]["model"], "verified": ["rc-easy", "rc-med", "rc-hard"], "dropped": 0},
                {"vector": "batch-and-persistence", "provider": POOL_5[3]["provider"], "model": POOL_5[3]["model"], "verified": ["rc-med", "rc-hard"], "dropped": 0},
            ],
        })
        self.assertEqual(step_k4["vectors"][0]["action"], "continue")

        step_k5 = eval_json({
            "worker_model": POOL_5[3],
            "reviewer_pool": POOL_5,
            "vectors": [{"name": "batch-and-persistence", "risk": "risky"}],
            "equivalence_checks": eq_checks("batch-and-persistence", ["rc-easy", "rc-med", "rc-hard"]),
            "reviews": [
                {"vector": "batch-and-persistence", "provider": POOL_5[0]["provider"], "model": POOL_5[0]["model"], "verified": ["rc-easy", "rc-med"], "dropped": 0},
                {"vector": "batch-and-persistence", "provider": POOL_5[1]["provider"], "model": POOL_5[1]["model"], "verified": ["rc-easy"], "minor": ["nit-comment"], "dropped": 0},
                {"vector": "batch-and-persistence", "provider": POOL_5[2]["provider"], "model": POOL_5[2]["model"], "verified": ["rc-easy", "rc-med", "rc-hard"], "dropped": 0},
                {"vector": "batch-and-persistence", "provider": POOL_5[3]["provider"], "model": POOL_5[3]["model"], "verified": ["rc-med", "rc-hard"], "dropped": 0},
                {"vector": "batch-and-persistence", "provider": POOL_5[4]["provider"], "model": POOL_5[4]["model"], "verified": ["rc-easy", "rc-med", "rc-hard"], "dropped": 0},
            ],
        })
        v5 = step_k5["vectors"][0]
        self.assertEqual(v5["action"], "stop")
        self.assertEqual(v5["verdict"], "saturated")
        self.assertEqual(v5["estimate"]["frequencies"], [0, 0, 1, 2, 0])

    def test_repeated_model_and_worker_only_low_risk_enforced_structurally(self):
        pool_sh = [
            {"provider": "anthropic", "model": "sonnet", "effort": "medium", "harness": "claude"},
            {"provider": "anthropic", "model": "haiku", "effort": "medium", "harness": "claude"},
        ]
        w_only = eval_json({
            "worker_model": pool_sh[1],
            "reviewer_pool": pool_sh,
            "vectors": [{"name": "cli", "risk": "low"}],
            "reviews": [
                {"vector": "cli", "provider": "anthropic", "model": "haiku", "verified": [], "dropped": 0},
            ],
        })
        self.assertEqual(w_only["vectors"][0]["action"], "continue")
        self.assertEqual(w_only["vectors"][0]["reason"], "non_worker_model_required")
        self.assertTrue(any("worker_model_only" in m for m in w_only["vectors"][0]["rule_violations"]))

        dup = eval_json({
            "reviewer_pool": POOL_4,
            "vectors": [{"name": "auth", "risk": "risky"}],
            "equivalence_checks": eq_checks("auth", ["rc-1"]),
            "reviews": [
                {"vector": "auth", "provider": "anthropic", "model": "claude-opus-4-6", "harness": "claude", "verified": ["rc-1"], "dropped": 0},
                {"vector": "auth", "provider": "openai", "model": "gpt-5.4", "harness": "codex", "verified": ["rc-1"], "dropped": 0},
                {"vector": "auth", "provider": "anthropic", "model": "claude-opus-4-6", "harness": "pi", "verified": ["rc-1"], "dropped": 0},
            ],
        })
        self.assertEqual(dup["vectors"][0]["action"], "continue")
        self.assertTrue(any("duplicate_model_on_vector" in m for m in dup["vectors"][0]["rule_violations"]))
        self.assertEqual(dup["vectors"][0]["estimate"]["estimator"], "chapman_hypergeometric_95")

    def test_unreachable_models_flag_pool_exhausted_block_risky_landing_and_populate_could_not_test(self):
        payload = {
            "target": "auth-refresh",
            "worker_model": {"provider": "anthropic", "model": "haiku", "harness": "claude"},
            "reviewer_pool": [
                {"provider": "anthropic", "model": "sonnet", "effort": "medium", "harness": "claude"},
                {"provider": "openai", "model": "default", "effort": "medium", "harness": "codex"},
            ],
            "unreachable_models": [
                {"provider": "openai", "model": "default", "harness": "codex", "reason": "codex CLI not installed"},
            ],
            "vectors": [{"name": "auth-security", "risk": "risky"}],
            "reviews": [
                {"vector": "auth-security", "provider": "anthropic", "model": "sonnet", "verified": ["rc-exp"], "dropped": 0},
            ],
        }
        data = eval_json(payload)
        vec = data["vectors"][0]
        self.assertEqual(vec["action"], "flag")
        self.assertEqual(vec["reason"], "remaining_pool_models_unreachable")
        self.assertTrue(vec["landing_blocked"])
        self.assertTrue(data["landing_blocked"])
        md = run_ledger(payload, "--markdown").stdout
        self.assertIn("LANDING BLOCKED", md)
        self.assertIn("codex CLI not installed", md)

    def test_boundary_validation_rejects_retired_or_unapproved_or_bad_calibration_with_exit_two(self):
        for bad in (
            {"roles": {"reviewer": {"provider": "anthropic", "model": "opus"}}, "reviewer_pool": POOL_4, "vectors": [{"name": "a", "risk": "low"}]},
            {"reviewer_pool": POOL_4[:1], "vectors": [{"name": "a", "risk": "low"}], "reviews": [{"vector": "a", "provider": "openai", "model": "unapproved", "verified": []}]},
            {"reviewer_pool": POOL_4, "vectors": [{"name": "a", "risk": "extreme"}]},
            {"reviewer_pool": POOL_4, "vectors": [{"name": "a", "risk": "low"}], "equivalence_checks": [{"vector": "a", "root_cause": "r", "reproductions": ["x"], "fix_verified": "yes"}]},
            {"reviewer_pool": POOL_4, "vectors": [{"name": "a", "risk": "low"}], "miss_risk_target": 1.5},
            {"reviewer_pool": POOL_4, "vectors": [{"name": "a", "risk": "low"}], "model_catch_rates": {"anthropic/claude-opus-4-6": {"detected": 6, "planted": 5}}},
            {"reviewer_pool": POOL_4, "vectors": [{"name": "a", "risk": "low"}], "model_catch_rates": {"anthropic/claude-opus-4-6": {"detected": 0, "planted": 0}}},
        ):
            res = run_ledger(bad)
            self.assertEqual(res.returncode, 2, f"expected exit 2 for {bad}")


if __name__ == "__main__":
    unittest.main()
