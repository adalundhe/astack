"""Tests for lean `bin/astack-review-ledger` and `lib/astack_ledger/` (gates, capture-recapture, risk & catch-table contracts)."""
from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "bin" / "astack-review-ledger"
sys.path.insert(0, str(ROOT / "lib"))

from astack_ledger import (  # noqa: E402
    atom_mass,
    bucket_feature_value,
    build_catch_table,
    catch_miss_at,
    change_residual_risk_with_bracket,
    check_finder_diagnostics,
    compose_change_risk,
    compose_vector_risk,
    fit_atom_risk_mixture,
    fit_clustering_phi,
    invert_risk_to_mass,
    residual_risk_with_bracket,
    score_vectors,
)

POOL_4 = [
    {"provider": "anthropic", "model": "claude-opus-4-6", "effort": "high", "harness": "claude", "cost_minutes": 2.0},
    {"provider": "openai", "model": "gpt-5.4", "effort": "high", "harness": "codex", "cost_minutes": 2.0},
    {"provider": "google", "model": "gemini-2.5-pro", "effort": "high", "harness": "agy", "cost_minutes": 2.0},
    {"provider": "anthropic", "model": "claude-sonnet-4-6", "effort": "medium", "harness": "claude", "cost_minutes": 2.0},
]


def run_ledger(payload: dict, *extra_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(BIN), "-", *extra_args],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )


def eval_json(payload: dict, *extra_args: str) -> dict:
    proc = run_ledger(payload, "--json", *extra_args)
    assert proc.returncode == 0, f"ledger failed ({proc.returncode}): {proc.stderr}"
    return json.loads(proc.stdout)


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
    return proc.stdout.strip()


class ReviewLedgerTest(unittest.TestCase):
    def test_boundary_validation_rejects_legacy_strings_out_of_range_and_unapproved_models(self):
        for bad in (
            {"roles": {"reviewer": {"provider": "anthropic", "model": "opus"}}, "reviewer_pool": POOL_4, "vectors": [{"name": "a", "risk": 0.0}]},
            {"reviewer_pool": POOL_4, "vectors": [{"name": "a", "risk": "low"}]},
            {"reviewer_pool": POOL_4, "vectors": [{"name": "a", "risk": "risky"}]},
            {"reviewer_pool": POOL_4, "vectors": [{"name": "a", "risk": "extreme"}]},
            {"reviewer_pool": POOL_4, "vectors": [{"name": "a", "risk": -0.05}]},
            {"reviewer_pool": POOL_4, "vectors": [{"name": "a", "risk": 1.0}]},
            {"reviewer_pool": POOL_4, "vectors": [{"name": "a", "risk": True}]},
            {"reviewer_pool": POOL_4[:1], "vectors": [{"name": "a", "risk": 0.0}], "reviews": [{"vector": "a", "provider": "openai", "model": "unapproved", "verified": []}]},
            {"reviewer_pool": POOL_4, "vectors": [{"name": "a", "risk": 0.0}], "equivalence_checks": [{"vector": "a", "root_cause": "r", "fix_verified": "yes"}]},
            {"reviewer_pool": POOL_4, "vectors": [{"name": "a", "risk": 0.0}], "miss_risk_target": 1.5},
            {"reviewer_pool": POOL_4, "vectors": [{"name": "a", "risk": 0.0}], "model_catch_rates": {"anthropic/claude-opus-4-6": {"detected": 6, "planted": 5}}},
            {"reviewer_pool": POOL_4, "vectors": [{"name": "a", "risk": 0.0}], "model_catch_rates": {"anthropic/claude-opus-4-6": {"detected": 0, "planted": 0}}},
            {"reviewer_pool": POOL_4, "vectors": [{"name": "a", "risk": 0.5}], "catch_table": {"provenance": "bogus"}},
            {"reviewer_pool": POOL_4, "vectors": [{"name": "a", "risk": 0.5}], "catch_table": {"provenance": "measured"}},
            {"reviewer_pool": POOL_4, "vectors": [{"name": "a", "risk": 0.5}], "catch_table": {"provenance": "anchored"}},
        ):
            res = run_ledger(bad)
            self.assertEqual(res.returncode, 2, f"expected exit 2 for {bad}")

    def test_structural_gates_zero_risk_seams_duplicates_worker_only_and_unreachable(self):
        # Zero-risk stops on 1 clean non-worker review; worker-only review flagged structurally
        w_only = eval_json({
            "worker_model": POOL_4[3],
            "reviewer_pool": [POOL_4[0], POOL_4[3]],
            "vectors": [{"name": "docs", "risk": 0.0}],
            "reviews": [{"vector": "docs", "provider": "anthropic", "model": "claude-sonnet-4-6", "verified": []}],
        })
        self.assertEqual(w_only["vectors"][0]["action"], "continue")
        self.assertEqual(w_only["vectors"][0]["reason"], "non_worker_model_required")
        self.assertIn("worker_model_only", w_only["vectors"][0]["rule_violations"])

        clean_zero = eval_json({
            "worker_model": POOL_4[3],
            "reviewer_pool": [POOL_4[0], POOL_4[3]],
            "vectors": [{"name": "docs", "risk": 0.0}],
            "reviews": [{"vector": "docs", "provider": "anthropic", "model": "claude-opus-4-6", "verified": []}],
        })
        self.assertEqual(clean_zero["overall"], "complete")
        self.assertEqual(clean_zero["vectors"][0]["reason"], "zero_risk_single_clean")

        # Verified native seam lets positive-risk vector stop after 1 clean reading-lane review; failed seam blocks
        seam_ok = eval_json({
            "reviewer_pool": POOL_4[:2],
            "seams": [{"seam": "wal-loom", "verdict": "clean", "cases_run": 64, "cases_failed": 0}],
            "vectors": [{"name": "wal", "risk": 0.65, "seams": ["wal-loom"]}],
            "reviews": [{"vector": "wal", "provider": "anthropic", "model": "claude-opus-4-6", "verified": []}],
        })
        self.assertEqual(seam_ok["overall"], "complete")
        self.assertEqual(seam_ok["vectors"][0]["reason"], "seam_verified_single_clean")

        seam_fail = eval_json({
            "reviewer_pool": POOL_4[:2],
            "seams": [{"seam": "wal-loom", "verdict": "failed", "cases_run": 64, "cases_failed": 2}],
            "vectors": [{"name": "wal", "risk": 0.65, "seams": ["wal-loom"]}],
            "reviews": [],
        })
        self.assertTrue(seam_fail["landing_blocked"])
        self.assertEqual(seam_fail["overall"], "flagged")

        # Duplicate model flagged + unreachable model blocks risky landing and prints LANDING BLOCKED
        unreach = eval_json({
            "target": "auth-refresh",
            "reviewer_pool": POOL_4[:2],
            "unreachable_models": [{"provider": "openai", "model": "gpt-5.4", "harness": "codex", "reason": "codex CLI missing"}],
            "vectors": [{"name": "auth", "risk": 0.63}],
            "reviews": [
                {"vector": "auth", "provider": "anthropic", "model": "claude-opus-4-6", "verified": ["rc-1"]},
                {"vector": "auth", "provider": "anthropic", "model": "claude-opus-4-6", "verified": ["rc-1"]},
            ],
        })
        vec = unreach["vectors"][0]
        self.assertEqual(vec["action"], "flag")
        self.assertEqual(vec["reason"], "remaining_pool_models_unreachable")
        self.assertTrue(any("duplicate_model_on_vector" in v for v in vec["rule_violations"]))
        self.assertTrue(unreach["landing_blocked"])
        md = run_ledger({
            "target": "auth-refresh",
            "reviewer_pool": POOL_4[:2],
            "unreachable_models": [{"provider": "openai", "model": "gpt-5.4", "reason": "codex CLI missing"}],
            "vectors": [{"name": "auth", "risk": 0.63}],
            "reviews": [{"vector": "auth", "provider": "anthropic", "model": "claude-opus-4-6", "verified": ["rc-1"]}],
        }, "--markdown").stdout
        self.assertIn("LANDING BLOCKED", md)
        self.assertIn("codex CLI missing", md)

    def test_capture_recapture_unanimous_small_count_reason_and_jackknife_mh(self):
        # 2 models unanimously find the exact same single bug with unused pool models remaining:
        # MUST emit unanimous_small_count_needs_capture_recapture_check (NOT models_still_finding_new_bugs!)
        unanimous = eval_json({
            "reviewer_pool": POOL_4,
            "vectors": [{"name": "wal", "risk": 0.63}],
            "reviews": [
                {"vector": "wal", "provider": "anthropic", "model": "claude-opus-4-6", "verified": ["rc-1"]},
                {"vector": "wal", "provider": "openai", "model": "gpt-5.4", "verified": ["rc-1"]},
            ],
        })
        v_un = unanimous["vectors"][0]
        self.assertEqual(v_un["action"], "continue")
        self.assertEqual(v_un["reason"], "unanimous_small_count_needs_capture_recapture_check")
        self.assertEqual(v_un["estimate"]["estimator"], "chapman_hypergeometric")
        # Default mode uses ZERO arbitrary confidence_alpha/Z_95 cutoff: reports exact p_at_least_one_unfound!
        self.assertIsNone(v_un["estimate"]["confidence_alpha"])
        self.assertAlmostEqual(v_un["estimate"]["p_at_least_one_unfound"], 0.5, places=4)
        self.assertIsNone(v_un["estimate"]["estimated_unfound_upper"])

        # Explicit confidence_alpha derives quantiles dynamically via statistics.NormalDist (no hardcoded Z_95!)
        explicit_alpha = eval_json({
            "reviewer_pool": POOL_4,
            "confidence_alpha": 0.05,
            "vectors": [{"name": "wal", "risk": 0.63}],
            "reviews": [
                {"vector": "wal", "provider": "anthropic", "model": "claude-opus-4-6", "verified": [f"b{i}" for i in range(20)]},
                {"vector": "wal", "provider": "openai", "model": "gpt-5.4", "verified": [f"b{i}" for i in range(20)]},
            ],
        })
        self.assertTrue(explicit_alpha["vectors"][0]["estimate"]["can_stop"])
        self.assertEqual(explicit_alpha["vectors"][0]["estimate"]["confidence_alpha"], 0.05)

        # Structural hygiene: zero hardcoded Z_95 magic floats and max control-flow nesting depth <= 2 in lib/astack_ledger/
        import ast

        def _depth(node: ast.AST, d: int = 0) -> int:
            nd = d + (1 if isinstance(node, (ast.If, ast.For, ast.While, ast.With, ast.Try)) else 0)
            return max([nd] + [_depth(c, nd) for c in ast.iter_child_nodes(node)])

        for py_file in sorted((ROOT / "lib" / "astack_ledger").glob("*.py")):
            src = py_file.read_text(encoding="utf-8")
            self.assertNotIn("Z_95", src, f"hardcoded Z_95 constant in {py_file.name}")
            tree = ast.parse(src)
            for fn in (n for n in tree.body if isinstance(n, ast.FunctionDef)):
                self.assertLessEqual(_depth(fn), 2, f"{py_file.name}:{fn.name} nesting depth > 2")

        # Distinct singletons MUST emit models_still_finding_new_bugs
        distinct = eval_json({
            "reviewer_pool": POOL_4,
            "vectors": [{"name": "wal", "risk": 0.63}],
            "reviews": [
                {"vector": "wal", "provider": "anthropic", "model": "claude-opus-4-6", "verified": ["rc-1"]},
                {"vector": "wal", "provider": "openai", "model": "gpt-5.4", "verified": ["rc-2"]},
            ],
        })
        self.assertEqual(distinct["vectors"][0]["reason"], "models_still_finding_new_bugs")

        # 3 reviewers with strong unanimous overlap -> jackknife_mh
        three = eval_json({
            "reviewer_pool": POOL_4[:3],
            "vectors": [{"name": "wal", "risk": 0.63}],
            "reviews": [
                {"vector": "wal", "provider": "anthropic", "model": "claude-opus-4-6", "verified": ["b1", "b2", "b3"]},
                {"vector": "wal", "provider": "openai", "model": "gpt-5.4", "verified": ["b1", "b2", "b3"]},
                {"vector": "wal", "provider": "google", "model": "gemini-2.5-pro", "verified": ["b1", "b2", "b3"]},
            ],
        })
        self.assertEqual(three["vectors"][0]["estimate"]["estimator"], "jackknife_mh")
        self.assertEqual(three["vectors"][0]["action"], "stop")
        self.assertEqual(three["vectors"][0]["verdict"], "fix_and_rereview")

    def test_pinned_scorer_invariants_power_of_two_closed_horizon_and_commit_grouping(self):
        # 3a) Power-of-two bucketing for finite numeric features (bools untouched)
        self.assertEqual(bucket_feature_value(0), "0")
        self.assertEqual(bucket_feature_value(1), "2^0")
        self.assertEqual(bucket_feature_value(2), "2^1")
        self.assertEqual(bucket_feature_value(3), "2^1")
        self.assertEqual(bucket_feature_value(4), "2^2")
        self.assertEqual(bucket_feature_value(7), "2^2")
        self.assertEqual(bucket_feature_value(True), "true")
        self.assertEqual(bucket_feature_value(False), "false")

        # Raw varied integers (100..159 vs 1..3) MUST be bucketed so size feature is selected and beats constant!
        train = []
        for i in range(60):
            big = (i % 2 == 0)
            train.append({
                "atom_id": f"a{i}",
                "order": i,
                "commit": f"c{i}",
                "file": "f.rs",
                "features": {"lines_changed": (100 + i) if big else (1 + (i % 2))},
                "fault_within_horizon": big,
            })
        # 3b) Closed horizon enforced directly by scorer: horizon=10 drops orders 50..59!
        mix = fit_atom_risk_mixture(
            train,
            [
                {"atom_id": "big", "commit": "c99", "file": "f.rs", "features": {"lines_changed": 120}},
                {"atom_id": "small", "commit": "c99", "file": "f.rs", "features": {"lines_changed": 2}},
            ],
            horizon=10,
        )
        self.assertEqual(mix["train_atoms_count"], 50)
        self.assertEqual(mix["dropped_open_horizon_atoms"], 10)
        self.assertTrue(mix["beats_constant"])
        self.assertIn("lines_changed", mix["selected_features"])
        by_id = {a["atom_id"]: a for a in mix["scored_atoms"]}
        self.assertGreater(by_id["big"]["q"], by_id["small"]["q"] * 3.0)

        # 3c) Whole-change risk MUST group by commit ID across vectors before clustering!
        phi = 1.5
        scored = score_vectors(
            [
                {"name": "v_lock", "commit_masses": {"c1": 0.6, "c2": 0.4}},
                {"name": "v_wal", "commit_masses": {"c1": 0.6, "c2": 0.4}},
            ],
            phi=phi,
        )
        expected_grouped = 1.0 - ((1.0 + phi * 1.2) ** (-1.0 / phi)) * ((1.0 + phi * 0.8) ** (-1.0 / phi))
        wrong_ungrouped = 1.0 - (((1.0 + phi * 0.6) ** (-1.0 / phi)) ** 2) * (((1.0 + phi * 0.4) ** (-1.0 / phi)) ** 2)
        self.assertAlmostEqual(scored["change_risk"], expected_grouped, places=5)
        self.assertLess(scored["change_risk"], wrong_ungrouped - 0.01)

        # Exact inverse round-trip & unbounded phi MLE (no 64.0 cap!)
        m_orig = 1.75
        p_val = compose_vector_risk({"c1": m_orig}, phi)
        self.assertAlmostEqual(invert_risk_to_mass(p_val, phi), m_orig, places=6)
        self.assertGreaterEqual(fit_clustering_phi([({"c1": 2.0}, False), ({"c1": 2.0}, False), ({"c1": 2.0}, True)]), 0.0)
        # Heavy overdispersion where true MLE phi >> 64 (must not clip at 64.0!)
        heavy_past = [({"c1": 50.0}, False)] * 19 + [({"c1": 50.0}, True)]
        self.assertGreater(fit_clustering_phi(heavy_past), 64.0)
        # Huge mass must STILL round strictly < 1.0 so score output always pipes cleanly into ledger!
        huge = score_vectors([{"name": "mega", "commit_masses": {"c1": 200.0}}], phi=0.0)
        self.assertLess(huge["change_risk"], 1.0)
        self.assertLess(huge["vectors"][0]["risk"], 1.0)
        piped = eval_json({"reviewer_pool": POOL_4[:2], "vectors": huge["vectors"], "reviews": []})
        self.assertEqual(piped["overall"], "continue")

    def test_anchored_catch_table_sharp_exchangeable_brackets_no_optimistic_point(self):
        # Amphora anchor: k0=2, caught=5, total=26 -> m0 = 21.5/27 = 0.796296
        ct = build_catch_table("anchored", anchor={"k": 2, "caught": 5, "total": 26}, max_k=16)
        m0 = 21.5 / 27.0
        self.assertEqual(ct["provenance"], "anchored")
        self.assertAlmostEqual(ct["miss_by_k"]["2"], m0, places=5)
        self.assertEqual(ct["miss_bracket_by_k"]["2"], [round(m0, 6), round(m0, 6)])

        # Off-anchor k in {1, 4, 8, 16}: point MUST be None (NEVER optimistic geometric m0^(k/k0)!)
        self.assertIsNone(ct["miss_by_k"]["1"])
        self.assertAlmostEqual(ct["miss_bracket_by_k"]["1"][0], m0, places=4)
        self.assertAlmostEqual(ct["miss_bracket_by_k"]["1"][1], m0 ** 0.5, places=4)
        for k in (4, 8, 16):
            self.assertIsNone(ct["miss_by_k"][str(k)], f"k={k} must not report optimistic point")
            lo, hi = ct["miss_bracket_by_k"][str(k)]
            self.assertAlmostEqual(lo, m0 ** (k / 2.0), places=4)
            self.assertAlmostEqual(hi, m0, places=4)
            # Internal allocation curve MUST lie strictly inside (lo, hi) with diminishing returns
            pt_k, alloc_k, lo_k, hi_k = catch_miss_at(ct, k)
            self.assertIsNone(pt_k)
            self.assertGreater(alloc_k, lo_k)
            self.assertLess(alloc_k, hi_k)

        # Ledger surfaces residual_risk=None off-anchor and commit-grouped residual bracket across vectors!
        res = eval_json({
            "reviewer_pool": POOL_4,
            "catch_table": {"provenance": "anchored", "anchor": {"k": 2, "caught": 5, "total": 26}},
            "vectors": [
                {"name": "v1", "risk": compose_vector_risk({"c1": 1.0}, 1.0), "phi": 1.0, "commit_masses": {"c1": 1.0}},
                {"name": "v2", "risk": compose_vector_risk({"c1": 1.0}, 1.0), "phi": 1.0, "commit_masses": {"c1": 1.0}},
            ],
            "reviews": [
                {"vector": "v1", "provider": "anthropic", "model": "claude-opus-4-6", "verified": []},
                {"vector": "v1", "provider": "openai", "model": "gpt-5.4", "verified": []},
                {"vector": "v1", "provider": "google", "model": "gemini-2.5-pro", "verified": []},
                {"vector": "v2", "provider": "anthropic", "model": "claude-opus-4-6", "verified": []},
                {"vector": "v2", "provider": "openai", "model": "gpt-5.4", "verified": []},
            ],
        })
        by_v = {v["name"]: v for v in res["vectors"]}
        self.assertIsNone(by_v["v1"]["residual_risk"])
        self.assertIsNotNone(by_v["v1"]["residual_risk_bracket"])
        self.assertIsNotNone(by_v["v2"]["residual_risk"])  # at exact anchor k=2
        self.assertIsNone(res["change_residual_risk"])     # v1 is off-anchor -> whole change point is None
        ch_lo, ch_hi = res["change_residual_risk_bracket"]
        self.assertLess(ch_lo, ch_hi)
        # Whole-change bracket must match commit-grouped computation
        expected = change_residual_risk_with_bracket([({"c1": 1.0}, 3), ({"c1": 1.0}, 2)], 1.0, ct)
        self.assertEqual(res["change_residual_risk_bracket"], expected["change_residual_risk_bracket"])

    def test_level_invariant_wave1_mass_allocation_plenty_tight_and_overrun_budgets(self):
        pool_1m = [{**m, "cost_minutes": 1.0} for m in POOL_4]
        validated_outcomes = [
            {
                "review_id": f"past-{i}",
                "vectors": [
                    {"name": "v_hot", "hist_share": 0.78, "reviewers_completed": 3, "observed_blockers": 2},
                    {"name": "v_mid", "hist_share": 0.18, "reviewers_completed": 2, "observed_blockers": 0},
                    {"name": "v_low", "hist_share": 0.04, "reviewers_completed": 1, "observed_blockers": 0},
                ],
            }
            for i in range(6)
        ]

        def _wave1(scale: float, budget_min: float, outcomes: list[dict] | None = None) -> dict:
            payload = {
                "reviewer_pool": pool_1m,
                "budget": {"budget_minutes": budget_min, "elapsed_minutes": 0.0},
                "vectors": [
                    {"name": "v_hot", "risk": compose_vector_risk({"c1": 17.6 * scale}, 1.0), "phi": 1.0, "mass": 17.6 * scale},
                    {"name": "v_mid", "risk": compose_vector_risk({"c2": 4.0 * scale}, 1.0), "phi": 1.0, "mass": 4.0 * scale},
                    {"name": "v_low", "risk": compose_vector_risk({"c3": 1.0 * scale}, 1.0), "phi": 1.0, "mass": 1.0 * scale},
                ],
                "reviews": [],
            }
            if outcomes is not None:
                payload["past_review_outcomes"] = outcomes
            return eval_json(payload)

        # 1a) Cold start (T=0, unvalidated scorer): dynamic gap share starts at 0.50 -> hedges (3 / 2 / 1) instead of starving mid!
        cold_1x = _wave1(1.0, 30.0)
        cold_10x = _wave1(10.0, 30.0)
        self.assertEqual({v["name"]: len(v["next_models"]) for v in cold_1x["vectors"]}, {"v_hot": 3, "v_mid": 2, "v_low": 1})
        self.assertEqual(
            {v["name"]: len(v["next_models"]) for v in cold_1x["vectors"]},
            {v["name"]: len(v["next_models"]) for v in cold_10x["vectors"]},
        )  # level-invariant!
        self.assertAlmostEqual(cold_1x["risk_allocation"]["dynamic_gap_share"], 0.5, places=4)
        self.assertFalse(cold_1x["risk_allocation"]["budget_exceeded"])
        self.assertEqual(cold_1x["risk_allocation"]["planned_cost"], 6.0)
        self.assertLess(cold_10x["change_risk"], 1.0)  # never rounds up to 1.0!

        # 1b) Validated scorer: dynamic gap share shrinks automatically -> sharpens to (4 / 1 / 1), still level-invariant!
        val_1x = _wave1(1.0, 30.0, validated_outcomes)
        val_10x = _wave1(10.0, 30.0, validated_outcomes)
        self.assertEqual({v["name"]: len(v["next_models"]) for v in val_1x["vectors"]}, {"v_hot": 4, "v_mid": 1, "v_low": 1})
        self.assertEqual(
            {v["name"]: len(v["next_models"]) for v in val_1x["vectors"]},
            {v["name"]: len(v["next_models"]) for v in val_10x["vectors"]},
        )
        self.assertLess(val_1x["risk_allocation"]["dynamic_gap_share"], 0.25)
        self.assertFalse(val_1x["scorer_calibration"]["miscalibrated_on_gaps"])

        # 2) Tight budget (6m): exact 6m spent, zero silent overspend!
        tight = _wave1(1.0, 6.0, validated_outcomes)
        self.assertEqual({v["name"]: len(v["next_models"]) for v in tight["vectors"]}, {"v_hot": 4, "v_mid": 1, "v_low": 1})
        self.assertFalse(tight["risk_allocation"]["budget_exceeded"])

        # 3) Very tight budget (3m for 3 vectors): 1 per vector = 3m, zero overspend!
        three_m = _wave1(1.0, 3.0)
        self.assertEqual({v["name"]: len(v["next_models"]) for v in three_m["vectors"]}, {"v_hot": 1, "v_mid": 1, "v_low": 1})
        self.assertFalse(three_m["risk_allocation"]["budget_exceeded"])

        # 4) Sub-minimum budget (2m for 3 vectors): minimum 1-per-vector floor exceeds budget -> explicitly flagged!
        over = _wave1(1.0, 2.0)
        self.assertTrue(over["risk_allocation"]["budget_exceeded"])
        self.assertEqual(over["risk_allocation"]["planned_cost"], 3.0)
        self.assertEqual(over["risk_allocation"]["budget_overrun"], 1.0)
        md_over = run_ledger({
            "reviewer_pool": pool_1m,
            "budget": {"budget_minutes": 2.0, "elapsed_minutes": 0.0},
            "vectors": [
                {"name": "v_hot", "risk": 0.8, "mass": 17.6},
                {"name": "v_mid", "risk": 0.5, "mass": 4.0},
                {"name": "v_low", "risk": 0.3, "mass": 1.0},
            ],
            "reviews": [],
        }, "--markdown").stdout
        self.assertIn("BUDGET OVERRUN", md_over)

    def test_additive_model_no_starvation_multi_commit_files_and_dynamic_gap_learning(self):
        # 1) Additive Bayesian model learns BOTH lines_changed AND file_prior_faults without Cartesian starvation!
        train = []
        for i in range(120):
            big_lines = (i % 2 == 0)
            hot_file = ((i // 2) % 2 == 0)
            fault = big_lines and hot_file
            train.append({
                "atom_id": f"a{i}",
                "order": i,
                "commit": f"c{i}",
                "file": f"f{i % 4}.rs",
                "features": {
                    "lines_changed": (512 + i) if big_lines else (2 + (i % 2)),
                    "file_prior_faults": (8 + (i % 3)) if hot_file else 0,
                    "files_in_commit": 1 + (i % 8),
                    "is_new_file": (i % 5 == 0),
                },
                "fault_within_horizon": fault,
            })
        mix = fit_atom_risk_mixture(
            train,
            [
                {"atom_id": "both", "commit": "c1", "file": "m.rs", "features": {"lines_changed": 600, "file_prior_faults": 9, "files_in_commit": 3, "is_new_file": False}},
                {"atom_id": "neither", "commit": "c2", "file": "m.rs", "features": {"lines_changed": 2, "file_prior_faults": 0, "files_in_commit": 3, "is_new_file": False}},
            ],
            horizon=0,
        )
        self.assertTrue(mix["beats_constant"])
        self.assertIn("lines_changed", mix["selected_features"])
        self.assertIn("file_prior_faults", mix["selected_features"])
        by_id = {a["atom_id"]: a for a in mix["scored_atoms"]}
        self.assertGreater(by_id["both"]["q"], by_id["neither"]["q"] * 2.5)
        self.assertGreater(by_id["both"]["epistemic_var"], 0.0)
        self.assertGreater(by_id["both"]["gap_mass"], 0.0)
        self.assertIn("lines_changed", by_id["both"]["feature_contributions"])

        # 2) Multi-commit file indexing: vector with files=["m.rs"] MUST sum ALL commits touching m.rs (not drop after 1st!)
        scored_multi = score_vectors(
            [{"name": "mem", "files": ["m.rs"]}],
            train_atoms=train,
            candidate_atoms=[
                {"atom_id": "c1:m.rs", "commit": "c1", "file": "m.rs", "features": {"lines_changed": 600, "file_prior_faults": 9, "files_in_commit": 3, "is_new_file": False}},
                {"atom_id": "c2:m.rs", "commit": "c2", "file": "m.rs", "features": {"lines_changed": 600, "file_prior_faults": 9, "files_in_commit": 3, "is_new_file": False}},
            ],
            horizon=0,
        )
        self.assertEqual(sorted(scored_multi["vectors"][0]["commit_masses"].keys()), ["c1", "c2"])
        self.assertGreater(scored_multi["vectors"][0]["gap_mass"], 0.0)
        self.assertEqual(len(scored_multi["gap_atoms"]), 2)

        # 3) Dynamic gap learning via --outcomes JSONL: when bugs hit low-hist/high-gap vectors, gap share surges & tags gap_brief!
        tmp = Path(tempfile.mkdtemp(prefix="astack-outcomes-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        outcomes_file = tmp / "scorer_outcomes.jsonl"
        gap_miss_outcomes = [
            {
                "review_id": f"pr-{i}",
                "vectors": [
                    {"name": "store", "hist_share": 0.75, "gap_share": 0.10, "reviewers_completed": 4, "observed_blockers": 0},
                    {"name": "memory-budget", "hist_share": 0.05, "gap_share": 0.75, "reviewers_completed": 1, "observed_blockers": 2},
                    {"name": "docs", "hist_share": 0.20, "gap_share": 0.15, "reviewers_completed": 1, "observed_blockers": 0},
                ],
            }
            for i in range(4)
        ]
        outcomes_file.write_text("\n".join(json.dumps(r) for r in gap_miss_outcomes) + "\n", encoding="utf-8")

        pool_1m = [{**m, "cost_minutes": 1.0} for m in POOL_4]
        payload = {
            "target": "amphora-branch",
            "reviewer_pool": pool_1m,
            "budget": {"budget_minutes": 30.0, "elapsed_minutes": 0.0},
            "vectors": [
                {"name": "store", "risk": 0.85, "mass": 17.6, "gap_mass": 0.2},
                {"name": "memory-budget", "risk": 0.25, "mass": 1.0, "gap_mass": 5.0},
                {"name": "docs", "risk": 0.30, "mass": 2.0, "gap_mass": 0.3},
            ],
            "reviews": [],
        }
        res_gap = eval_json(payload, "--outcomes", str(outcomes_file))
        self.assertTrue(res_gap["scorer_calibration"]["miscalibrated_on_gaps"])
        self.assertGreater(res_gap["risk_allocation"]["dynamic_gap_share"], 0.75)
        by_v = {v["name"]: v for v in res_gap["vectors"]}
        self.assertGreater(len(by_v["memory-budget"]["next_models"]), len(by_v["store"]["next_models"]))
        self.assertEqual(by_v["memory-budget"]["brief_mode"], "gap_brief")
        self.assertTrue(any("memory-budget" in a and "gap_brief" in a for a in res_gap["next_actions"]))
        self.assertIn("outcome_record", res_gap)
        md_gap = run_ledger(payload, "--outcomes", str(outcomes_file), "--markdown").stdout
        self.assertIn("SCORER MISCALIBRATED ON GAPS", md_gap)

        # 4) Confirmation-bias debiasing: equal true bug rate across k=4 vs k=1 (proportional to c(k)) must NOT falsely crown hist!
        # With prior catch_table: c(1)=0.50, c(4)=1 - 35/128 = 0.7265625.
        # If hist gives 0.80 to A and 0.20 to B, while true bugs are equal (50/50 -> observed ~ 73 vs 50), unif beats hist!
        debiased = eval_json({
            "reviewer_pool": pool_1m,
            "vectors": [
                {"name": "a", "risk": 0.7, "mass": 4.0},
                {"name": "b", "risk": 0.3, "mass": 1.0},
            ],
            "past_review_outcomes": [
                {
                    "review_id": "debias-1",
                    "vectors": [
                        {"name": "a", "hist_share": 0.80, "reviewers_completed": 4, "observed_blockers": 3},
                        {"name": "b", "hist_share": 0.20, "reviewers_completed": 1, "observed_blockers": 2},
                    ],
                }
            ],
            "reviews": [],
        })
        self.assertGreater(debiased["scorer_calibration"]["weights"]["unif"], debiased["scorer_calibration"]["weights"]["hist"])

    def test_git_baseline_score_subcommand_and_raw_finder_diagnostics_without_boolean_cutoff(self):
        tmp = Path(tempfile.mkdtemp(prefix="astack-git-baseline-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        _git(tmp, "init", "-q")
        _git(tmp, "config", "user.email", "test@example.com")
        _git(tmp, "config", "user.name", "Tester")

        (tmp / "core.rs").write_text("fn a() -> i32 { 1 }\nfn b() -> i32 { 2 }\n")
        _git(tmp, "add", ".")
        _git(tmp, "commit", "-q", "-m", "initial")
        c0 = _git(tmp, "rev-parse", "HEAD")

        # Buggy commit + real git revert
        (tmp / "core.rs").write_text("fn a() -> i32 { 999 }\nfn b() -> i32 { 2 }\n")
        _git(tmp, "add", ".")
        _git(tmp, "commit", "-q", "-m", "change a")
        c_bug = _git(tmp, "rev-parse", "HEAD")
        _git(tmp, "revert", "--no-edit", c_bug)

        # Several filler commits (including single-tab lines inside commit bodies — regression for numstat parsing!)
        for i in range(6):
            (tmp / "util.rs").write_text(f"fn u() -> i32 {{ {i} }}\n")
            _git(tmp, "add", ".")
            _git(tmp, "commit", "-q", "-m", f"update util {i}\n\ncol_a\tcol_b\n1\t2\tfake_body.rs")
        base_sha = _git(tmp, "rev-parse", "HEAD")

        # Candidate change touching core.rs and util.rs
        (tmp / "core.rs").write_text("fn a() -> i32 { 1 }\nfn b() -> i32 { 3 }\n")
        (tmp / "util.rs").write_text("fn u() -> i32 { 99 }\n")
        _git(tmp, "add", ".")
        _git(tmp, "commit", "-q", "-m", "candidate diff")

        proc = subprocess.run(
            [sys.executable, "-B", str(BIN), "score", "--repo", str(tmp), "--base", base_sha, "--head", "HEAD", "--horizon", "2", "--json"],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["source"], "baseline_git")
        self.assertGreaterEqual(data["change_risk"], 0.0)
        self.assertLess(data["change_risk"], 1.0)

        # Raw finder diagnostics: NO boolean level_trusted or fix_rate_stable cutoffs!
        fc = data["finder_checks"]
        self.assertEqual(fc["reverts_checked"], 1)
        self.assertEqual(fc["reverts_recovered"], 1)
        self.assertEqual(fc["revert_recovery_rate"], 1.0)
        self.assertEqual(fc["level_status"], "unverified")
        self.assertNotIn("level_trusted", fc)
        self.assertNotIn("fix_rate_stable", fc)
        self.assertTrue(len(fc["slice_fix_rates"]) >= 1)

        # Direct check_finder_diagnostics agrees
        diag = check_finder_diagnostics(tmp, [{"introducing_commit": c0, "fix_commit": c_bug}])
        self.assertEqual(diag["level_status"], "unverified")
        self.assertNotIn("level_trusted", diag)
        self.assertNotIn("fix_rate_stable", diag)


if __name__ == "__main__":
    unittest.main()
