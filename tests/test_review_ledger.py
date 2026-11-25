"""Behaviour tests for bin/astack-review-ledger: blocking-only estimates, fix-equivalence overlap checks,
cautious k=2 exact hypergeometric lower/upper bounds, k>=3 Burnham-Overton + Beta-Binomial M_h 95% CI,
zero-finding risky-vector guard, risky landing gate, cross-harness metadata, unreachable models,
and Monte Carlo calibration verification."""
import importlib.machinery
import importlib.util
import json
import random
import subprocess
import sys
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


def eval_json(payload):
    res = run_ledger(payload, "--json")
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
        # Point 1: Minor suggestions/nits are reported separately and NEVER prevent a clean low-risk stop.
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
        self.assertEqual(vec["reason"], "clean_single_review")
        self.assertEqual(vec["verified_count"], 0)
        self.assertEqual(vec["minor_count"], 3)
        self.assertEqual(vec["dropped_count"], 1)
        self.assertFalse(vec["landing_blocked"])

    def test_low_risk_clean_two_reviews_still_stops_cleanly(self):
        # Low-risk vector with worker + non-worker clean reviews stops cleanly without needing 5 reviewers.
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

    def test_risky_vector_with_one_reviewer_never_stops_and_adds_second_model(self):
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

    def test_k2_cautious_upper_bound_refuses_premature_stop_on_small_counts(self):
        # With n1=8, n2=6, m=5, Chapman point unfound is 0.5,
        # but exact hypergeometric 95% upper bound is 7 >= 1 -> MUST CONTINUE (adds 3rd reviewer).
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
        self.assertEqual(vec["reason"], "cautious_upper_at_least_one")
        est = vec["estimate"]
        self.assertEqual(est["estimator"], "chapman_hypergeometric_95")
        self.assertAlmostEqual(est["estimated_unfound"], 0.5)
        self.assertGreaterEqual(est["estimated_unfound_upper"], 5.0)
        self.assertEqual(vec["next_models"][0]["model"], "gemini-2.5-pro")

    def test_k2_exact_hypergeometric_lower_and_upper_bounds(self):
        # Exact lower bound must NOT always collapse to 0 when overlap is low relative to sample sizes,
        # and exact upper bound must resolve without an arbitrary search cap when m >= 1.
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

    def test_k2_identical_small_finds_still_requires_third_reviewer(self):
        # Even when 2 reviewers find the exact same 2 bugs (n1=2, n2=2, m=2), exact hypergeometric
        # 95% upper bound is 4 unfound bugs >= 1 -> does NOT stop prematurely at k=2!
        shared = ["rc-1", "rc-2"]
        data = eval_json({
            "reviewer_pool": POOL_4,
            "vectors": [{"name": "seams", "risk": "risky"}],
            "equivalence_checks": eq_checks("seams", shared),
            "reviews": [
                {"vector": "seams", "provider": "anthropic", "model": "claude-opus-4-6", "verified": shared, "dropped": 0},
                {"vector": "seams", "provider": "openai", "model": "gpt-5.4", "verified": shared, "dropped": 0},
            ],
        })
        vec = data["vectors"][0]
        self.assertEqual(vec["action"], "continue")
        self.assertEqual(vec["estimate"]["estimated_unfound"], 0.0)
        self.assertEqual(vec["estimate"]["estimated_unfound_lower"], 0.0)
        self.assertEqual(vec["estimate"]["estimated_unfound_upper"], 4.0)

    def test_zero_bug_risky_vector_never_stops_at_k2_to_k4_and_clears_at_k5(self):
        # Risky vector with D=0 must NOT stop at k=2 (25% miss rate for a p=0.5 bug), k=3 (12.5%), or k=4 (6.25%).
        # It blocks landing if the pool runs out early, and clears cleanly once k=5 independent reviewers find 0 blocking bugs (3.125% < 5%).
        def clean_reviews(n):
            return [
                {
                    "vector": "seams",
                    "provider": POOL_5[i]["provider"],
                    "model": POOL_5[i]["model"],
                    "verified": [],
                    "minor": [f"nit-{i}"],
                    "dropped": 1,
                }
                for i in range(n)
            ]

        for k in (2, 3, 4):
            cont = eval_json({
                "reviewer_pool": POOL_5,
                "vectors": [{"name": "seams", "risk": "risky"}],
                "reviews": clean_reviews(k),
            })
            vec = cont["vectors"][0]
            self.assertEqual(vec["action"], "continue", f"expected continue at k={k}")
            self.assertEqual(vec["reason"], "zero_bugs_need_more_independent_reviews")
            self.assertGreaterEqual(vec["estimate"]["estimated_unfound_upper"], 1.0)
            self.assertAlmostEqual(vec["estimate"]["zero_bug_miss_prob"], 0.5**k, places=4)

        # If a smaller pool runs out at k=2 with 0 bugs on a risky vector -> flags landing_blocked with plain miss risk
        exhausted = eval_json({
            "reviewer_pool": POOL_5[:2],
            "vectors": [{"name": "seams", "risk": "risky"}],
            "reviews": clean_reviews(2),
        })
        self.assertEqual(exhausted["overall"], "flagged")
        self.assertTrue(exhausted["landing_blocked"])
        self.assertIn("25% chance", exhausted["person_decisions"][0]["question"])

        # At k=5 independent clean reviews -> 0.5^5 = 0.03125 < 0.05 -> clears cleanly!
        cleared = eval_json({
            "reviewer_pool": POOL_5,
            "vectors": [{"name": "seams", "risk": "risky"}],
            "reviews": clean_reviews(5),
        })
        vec5 = cleared["vectors"][0]
        self.assertEqual(vec5["action"], "stop")
        self.assertEqual(vec5["reason"], "zero_bug_confidence_reached")
        self.assertFalse(vec5["landing_blocked"])
        self.assertLess(vec5["estimate"]["estimated_unfound_upper"], 1.0)

    def test_k2_large_complete_overlap_stops_when_exact_hypergeometric_upper_below_one(self):
        # At n1=20, n2=20, m=20, P(M=20 | N=21) = 1/21 = 0.0476 < 0.05 -> exact upper unfound = 0 < 1 -> stops!
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

    def test_point_2_unverified_overlap_merge_is_rejected_and_split(self):
        # Claiming the same root cause ID across reviewers WITHOUT a fix-verified equivalence check
        # MUST NOT count as overlap; it is split into distinct findings and flagged under rule_violations!
        shared_5 = [f"rc-{i}" for i in range(1, 6)]
        data = eval_json({
            "reviewer_pool": POOL_5,
            "vectors": [{"name": "auth", "risk": "risky"}],
            "reviews": [
                {"vector": "auth", "provider": POOL_5[i]["provider"], "model": POOL_5[i]["model"], "verified": shared_5, "dropped": 0}
                for i in range(4)
            ],
        })
        vec = data["vectors"][0]
        self.assertEqual(vec["action"], "continue")
        self.assertTrue(any("unverified_overlap_merge" in v for v in vec["rule_violations"]))
        self.assertEqual(vec["estimate"]["estimator"], "jackknife_mh")
        self.assertEqual(vec["estimate"]["recaptured"], 0)
        self.assertFalse(vec["estimate"]["informative"])

        # Same reviews WITH fix_verified=False -> STILL rejected!
        data_false = eval_json({
            "reviewer_pool": POOL_5,
            "vectors": [{"name": "auth", "risk": "risky"}],
            "equivalence_checks": [
                {"vector": "auth", "root_cause": rc, "reproductions": [f"r-{rc}-1.py", f"r-{rc}-2.py"], "fix_verified": False}
                for rc in shared_5
            ],
            "reviews": [
                {"vector": "auth", "provider": POOL_5[i]["provider"], "model": POOL_5[i]["model"], "verified": shared_5, "dropped": 0}
                for i in range(4)
            ],
        })
        self.assertEqual(data_false["vectors"][0]["action"], "continue")

        # Once fix_verified=True proves all 5 shared root causes across 4 reviewers -> freqs=[0,0,0,5] -> STOPS cleanly!
        data_ok = eval_json({
            "reviewer_pool": POOL_5,
            "vectors": [{"name": "auth", "risk": "risky"}],
            "equivalence_checks": eq_checks("auth", shared_5),
            "reviews": [
                {"vector": "auth", "provider": POOL_5[i]["provider"], "model": POOL_5[i]["model"], "verified": shared_5, "dropped": 0}
                for i in range(4)
            ],
        })
        vec_ok = data_ok["vectors"][0]
        self.assertEqual(vec_ok["action"], "stop")
        self.assertEqual(vec_ok["estimate"]["estimator"], "jackknife_mh")
        self.assertEqual(vec_ok["estimate"]["frequencies"], [0, 0, 0, 5])
        self.assertEqual(vec_ok["estimate"]["estimated_unfound_upper"], 0.0)

    def test_beta_binomial_prevents_f1_zero_collapse_and_is_monotone_for_strong_consensus(self):
        # f1=0 alone must NOT collapse the 95% upper bound to 0 when heterogeneity could hide a harder bug.
        # 1) t=3, freqs=[0, 0, 2] -> continues (only 3 reviewers cannot rule out 1 harder bug)
        data_t3 = eval_json({
            "reviewer_pool": POOL_5,
            "vectors": [{"name": "auth", "risk": "risky"}],
            "equivalence_checks": eq_checks("auth", ["rc-1", "rc-2"]),
            "reviews": [
                {"vector": "auth", "provider": POOL_5[i]["provider"], "model": POOL_5[i]["model"], "verified": ["rc-1", "rc-2"], "dropped": 0}
                for i in range(3)
            ],
        })
        self.assertEqual(data_t3["vectors"][0]["action"], "continue")
        self.assertGreaterEqual(data_t3["vectors"][0]["estimate"]["estimated_unfound_upper"], 1.0)

        # 2) t=4, freqs=[0, 2, 1, 1] -> continues (2 bugs seen by only half the reviewers -> harder bug plausible!)
        data_t4_weak = eval_json({
            "reviewer_pool": POOL_5,
            "vectors": [{"name": "storage", "risk": "risky"}],
            "equivalence_checks": eq_checks("storage", ["rc-1", "rc-2", "rc-3", "rc-hard"]),
            "reviews": [
                {"vector": "storage", "provider": POOL_5[0]["provider"], "model": POOL_5[0]["model"], "verified": ["rc-1", "rc-2", "rc-3"], "dropped": 0},
                {"vector": "storage", "provider": POOL_5[1]["provider"], "model": POOL_5[1]["model"], "verified": ["rc-1", "rc-2"], "dropped": 0},
                {"vector": "storage", "provider": POOL_5[2]["provider"], "model": POOL_5[2]["model"], "verified": ["rc-1", "rc-2", "rc-3", "rc-hard"], "dropped": 0},
                {"vector": "storage", "provider": POOL_5[3]["provider"], "model": POOL_5[3]["model"], "verified": ["rc-1", "rc-hard"], "dropped": 0},
            ],
        })
        self.assertEqual(data_t4_weak["vectors"][0]["action"], "continue")
        self.assertEqual(data_t4_weak["vectors"][0]["estimate"]["frequencies"], [0, 2, 1, 1])
        self.assertGreaterEqual(data_t4_weak["vectors"][0]["estimate"]["estimated_unfound_upper"], 1.0)

        # 3) Strong consensus stays strictly monotone for large D (e.g. D=5, D=10, D=20 all caught by 4/4 reviewers -> STOP!)
        mod = _load_ledger_module()
        for D in (5, 10, 20):
            est = mod.jackknife_mh_estimate([0, 0, 0, D], 4)
            self.assertTrue(est["can_stop"], f"expected stop at t=4 freqs=[0,0,0,{D}], got {est}")
            self.assertEqual(est["estimated_unfound_upper"], 0.0)

        # 4) t=5 strong recapture freqs=[0, 0, 1, 2, 2] -> STOPS cleanly!
        est5 = mod.jackknife_mh_estimate([0, 0, 1, 2, 2], 5)
        self.assertTrue(est5["can_stop"])
        self.assertEqual(est5["estimated_unfound_upper"], 0.0)

    def test_point_3_k3_jackknife_continues_while_uncertain_and_stops_on_5_reviewer_consensus(self):
        # 3 reviewers: bug rc-hard found only by reviewer 3 (f1=1, f2=1, f3=2) -> MUST CONTINUE!
        data_cont = eval_json({
            "reviewer_pool": POOL_5,
            "vectors": [{"name": "storage", "risk": "risky"}],
            "equivalence_checks": eq_checks("storage", ["rc-1", "rc-2", "rc-3"]),
            "reviews": [
                {"vector": "storage", "provider": POOL_5[0]["provider"], "model": POOL_5[0]["model"], "verified": ["rc-1", "rc-2", "rc-3"], "dropped": 0},
                {"vector": "storage", "provider": POOL_5[1]["provider"], "model": POOL_5[1]["model"], "verified": ["rc-1", "rc-2"], "dropped": 0},
                {"vector": "storage", "provider": POOL_5[2]["provider"], "model": POOL_5[2]["model"], "verified": ["rc-1", "rc-2", "rc-3", "rc-hard"], "dropped": 0},
            ],
        })
        v = data_cont["vectors"][0]
        self.assertEqual(v["action"], "continue")
        self.assertEqual(v["estimate"]["estimator"], "jackknife_mh")
        self.assertEqual(v["estimate"]["frequencies"], [1, 1, 2])
        self.assertLess(v["estimate"]["estimated_unfound"], 1.0)
        self.assertGreater(v["estimate"]["estimated_unfound_upper"], 1.0)
        self.assertEqual(v["next_models"][0]["model"], "claude-sonnet-4-6")

        # 5th reviewer independently confirms all bugs -> freqs=[0, 0, 1, 2, 1] -> STOPS cleanly!
        data_stop = eval_json({
            "reviewer_pool": POOL_5,
            "vectors": [{"name": "storage", "risk": "risky"}],
            "equivalence_checks": eq_checks("storage", ["rc-1", "rc-2", "rc-3", "rc-hard"]),
            "reviews": [
                {"vector": "storage", "provider": POOL_5[0]["provider"], "model": POOL_5[0]["model"], "verified": ["rc-1", "rc-2", "rc-3"], "dropped": 0},
                {"vector": "storage", "provider": POOL_5[1]["provider"], "model": POOL_5[1]["model"], "verified": ["rc-1", "rc-2", "rc-3"], "dropped": 0},
                {"vector": "storage", "provider": POOL_5[2]["provider"], "model": POOL_5[2]["model"], "verified": ["rc-1", "rc-2", "rc-3", "rc-hard"], "dropped": 0},
                {"vector": "storage", "provider": POOL_5[3]["provider"], "model": POOL_5[3]["model"], "verified": ["rc-1", "rc-2", "rc-hard"], "dropped": 0},
                {"vector": "storage", "provider": POOL_5[4]["provider"], "model": POOL_5[4]["model"], "verified": ["rc-1", "rc-3", "rc-hard"], "dropped": 0},
            ],
        })
        v_stop = data_stop["vectors"][0]
        self.assertEqual(v_stop["action"], "stop")
        self.assertEqual(v_stop["estimate"]["frequencies"], [0, 0, 1, 2, 1])
        self.assertEqual(v_stop["estimate"]["estimated_unfound_upper"], 0.0)

    def test_point_4_run_out_pool_blocks_landing_on_risky_vector_with_range_and_plain_decision(self):
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
        self.assertFalse(by_v["formatting"]["landing_blocked"])  # only risky vectors block landing
        self.assertEqual(len(data["person_decisions"]), 1)
        decision = data["person_decisions"][0]
        self.assertEqual(decision["area"], "concurrency")
        self.assertEqual(decision["proven_blocking"], 3)
        self.assertIsNotNone(decision["estimated_remaining"])
        self.assertEqual(len(decision["estimated_remaining_range"]), 2)
        self.assertIn("Approve additional reviewer models", decision["question"])
        self.assertNotIn("POOL EXHAUSTED", decision["question"])

    def test_point_5_planted_bugs_of_varying_difficulty_never_stop_prematurely_and_stop_on_consensus(self):
        # Planted bugs: easy (rc-easy), medium (rc-med), hard (rc-hard) + 1 minor nit (nit-comment).
        # Step 1 (k=2): Reviewer 1 finds [rc-easy, rc-med], Reviewer 2 finds [rc-easy] + minor nit -> MUST NOT STOP!
        step_k2 = eval_json({
            "worker_model": POOL_5[3],
            "reviewer_pool": POOL_5,
            "vectors": [{"name": "batch-and-persistence", "risk": "risky"}],
            "equivalence_checks": eq_checks("batch-and-persistence", ["rc-easy"]),
            "reviews": [
                {"vector": "batch-and-persistence", "provider": POOL_5[0]["provider"], "model": POOL_5[0]["model"], "verified": ["rc-easy", "rc-med"], "dropped": 0},
                {"vector": "batch-and-persistence", "provider": POOL_5[1]["provider"], "model": POOL_5[1]["model"], "verified": ["rc-easy"], "minor": ["nit-comment"], "dropped": 0},
            ],
        })
        self.assertEqual(step_k2["vectors"][0]["action"], "continue")

        # Step 2 (k=3): Reviewer 3 catches rc-med AND uncovers rc-hard -> rc-hard is a singleton (f1=1) -> MUST NOT STOP!
        step_k3 = eval_json({
            "worker_model": POOL_5[3],
            "reviewer_pool": POOL_5,
            "vectors": [{"name": "batch-and-persistence", "risk": "risky"}],
            "equivalence_checks": eq_checks("batch-and-persistence", ["rc-easy", "rc-med"]),
            "reviews": [
                {"vector": "batch-and-persistence", "provider": POOL_5[0]["provider"], "model": POOL_5[0]["model"], "verified": ["rc-easy", "rc-med"], "dropped": 0},
                {"vector": "batch-and-persistence", "provider": POOL_5[1]["provider"], "model": POOL_5[1]["model"], "verified": ["rc-easy"], "minor": ["nit-comment"], "dropped": 0},
                {"vector": "batch-and-persistence", "provider": POOL_5[2]["provider"], "model": POOL_5[2]["model"], "verified": ["rc-easy", "rc-med", "rc-hard"], "dropped": 0},
            ],
        })
        self.assertEqual(step_k3["vectors"][0]["action"], "continue")
        self.assertEqual(step_k3["vectors"][0]["estimate"]["estimator"], "jackknife_mh")
        self.assertEqual(step_k3["vectors"][0]["estimate"]["frequencies"], [1, 1, 1])

        # Step 3 (k=4): Reviewer 4 confirms rc-hard (freqs=[0, 1, 2, 0]) -> still too thin to rule out another hard bug -> CONTINUES!
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
        self.assertEqual(step_k4["vectors"][0]["estimate"]["frequencies"], [0, 1, 2, 0])

        # Step 4 (k=5): Reviewer 5 confirms all 3 planted bugs and finds no new bugs -> freqs=[0, 0, 1, 2, 0] -> STOPS cleanly!
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
        self.assertEqual(v5["estimate"]["frequencies"], [0, 0, 1, 2, 0])
        self.assertEqual(v5["verified_root_causes"], ["rc-easy", "rc-hard", "rc-med"])
        self.assertEqual(v5["minor_findings"], ["nit-comment"])

    def test_monte_carlo_cautious_calibration_controls_false_stops(self):
        # Deterministic calibration check directly against chapman_estimate & jackknife_mh_estimate:
        # With 4- and 5-model pools, overall false-stop rate (stopped while >=1 bug remained missed)
        # stays <= 5.5% under p=0.5 homogeneity AND heterogeneous [0.8, 0.5, 0.2], while N=0 clears 100% at pool=5.
        mod = _load_ledger_module()
        memo: dict[tuple[int, tuple[int, ...]], bool] = {}

        def can_stop_k(counts: list[int], k: int) -> bool:
            D = sum(1 for c in counts if c > 0)
            if D == 0:
                _, _, ok = mod._zero_bug_upper_bound(k)
                return ok
            if k == 2:
                return False  # only stops at m >= 20
            freqs = [0] * k
            for c in counts:
                if c > 0:
                    freqs[c - 1] += 1
            key = (k, tuple(freqs))
            if key not in memo:
                memo[key] = bool(mod.jackknife_mh_estimate(freqs, k)["can_stop"])
            return memo[key]

        def run_sim(pool: int, probs: list[float], trials: int = 800) -> tuple[float, float]:
            rng = random.Random(42)
            done = 0
            false_stops = 0
            for _ in range(trials):
                counts = [0] * len(probs)
                stopped = False
                for k in range(1, pool + 1):
                    for i, p in enumerate(probs):
                        if rng.random() < p:
                            counts[i] += 1
                    if k >= 2 and can_stop_k(counts, k):
                        stopped = True
                        break
                if stopped:
                    done += 1
                    if any(c == 0 for c in counts):
                        false_stops += 1
            return done / trials, false_stops / trials

        done_zero, err_zero = run_sim(5, [], trials=200)
        self.assertEqual(done_zero, 1.0)
        self.assertEqual(err_zero, 0.0)

        for pool, probs in (
            (4, [0.5]),
            (4, [0.5, 0.5, 0.5]),
            (4, [0.5] * 6),
            (4, [0.8, 0.5, 0.2]),
            (5, [0.5]),
            (5, [0.5, 0.5, 0.5]),
            (5, [0.5] * 6),
        ):
            _, false_stop = run_sim(pool, probs, trials=800)
            self.assertLessEqual(
                false_stop,
                0.055,
                f"false-stop rate {false_stop:.3f} exceeded 5.5% for pool={pool}, probs={probs}",
            )

    def test_repeated_model_and_worker_only_low_risk_enforced_structurally(self):
        pool_sh = [
            {"provider": "anthropic", "model": "sonnet", "effort": "medium", "harness": "claude"},
            {"provider": "anthropic", "model": "haiku", "effort": "medium", "harness": "claude"},
        ]
        # Worker-only low-risk clean review cannot stop when a non-worker model is available
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

        # Repeat of same model on one vector (even via another harness) is excluded & flagged
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
        # Only 2 distinct models -> stays on chapman_hypergeometric_95 (not jackknife_mh!)
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
        self.assertEqual(len(data["person_decisions"]), 1)
        md = run_ledger(payload, "--markdown").stdout
        self.assertIn("LANDING BLOCKED", md)
        self.assertIn("codex CLI not installed", md)

    def test_boundary_validation_rejects_retired_or_unapproved_inputs_with_exit_two(self):
        for bad in (
            {"roles": {"reviewer": {"provider": "anthropic", "model": "opus"}}, "reviewer_pool": POOL_4, "vectors": [{"name": "a", "risk": "low"}]},
            {"reviewer_pool": POOL_4[:1], "vectors": [{"name": "a", "risk": "low"}], "reviews": [{"vector": "a", "provider": "openai", "model": "unapproved", "verified": []}]},
            {"reviewer_pool": POOL_4, "vectors": [{"name": "a", "risk": "extreme"}]},
            {"reviewer_pool": POOL_4, "vectors": [{"name": "a", "risk": "low"}], "equivalence_checks": [{"vector": "a", "root_cause": "r", "reproductions": ["x"], "fix_verified": "yes"}]},
        ):
            res = run_ledger(bad)
            self.assertEqual(res.returncode, 2, f"expected exit 2 for {bad}")


if __name__ == "__main__":
    unittest.main()
