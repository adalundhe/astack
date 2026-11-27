"""Lean mechanical review ledger: strict validation, gates, capture-recapture, and dynamic gap allocation."""
from __future__ import annotations

import json
import math
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_EPS = sys.float_info.epsilon
_SQRT_EPS = math.sqrt(_EPS)

from astack_ledger.capture import chapman_estimate, format_plain_range, jackknife_mh_estimate
from astack_ledger.risk import (
    VALID_RISK_TARGETS,
    build_catch_table,
    catch_miss_at,
    change_residual_risk_with_bracket,
    compose_change_risk,
    invert_risk_to_mass,
    residual_risk_with_bracket,
    round_risk,
)


class ValidationError(ValueError):
    """Raised when ledger input violates schema or safety boundaries (CLI exits 2)."""


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    model: str
    effort: str = ""
    harness: str = ""
    cost_minutes: float | None = None

    @property
    def key(self) -> tuple[str, str]:
        return (self.provider, self.model)

    @property
    def label(self) -> str:
        return f"{self.provider}/{self.model}"

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"provider": self.provider, "model": self.model}
        if self.effort:
            out["effort"] = self.effort
        if self.harness:
            out["harness"] = self.harness
        if self.cost_minutes is not None:
            out["cost_minutes"] = self.cost_minutes
        return out


@dataclass(frozen=True)
class CatchRate:
    detected: int
    planted: int
    per_bug: dict[str, tuple[int, int]] = field(default_factory=dict)


def _req_str(obj: Any, field_name: str) -> str:
    if not isinstance(obj, str) or not obj.strip():
        raise ValidationError(f"{field_name} must be a non-empty string")
    return obj.strip()


def _parse_open_unit_float(val: Any, name: str) -> float | None:
    if val is None:
        return None
    if isinstance(val, bool) or not isinstance(val, (int, float)) or not (0.0 < float(val) < 1.0):
        raise ValidationError(f"{name} must be strictly between 0 and 1")
    return float(val)


def _parse_nonneg_float(val: Any, name: str) -> float | None:
    if val is None:
        return None
    if isinstance(val, bool) or not isinstance(val, (int, float)) or float(val) < 0.0:
        raise ValidationError(f"{name} must be >= 0")
    return float(val)


def _parse_model(raw: Any, ctx: str) -> ModelSpec:
    if not isinstance(raw, dict):
        raise ValidationError(f"{ctx} must be an object")
    prov = _req_str(raw.get("provider"), f"{ctx}.provider")
    mod = _req_str(raw.get("model"), f"{ctx}.model")
    cost_raw = raw.get("cost_minutes")
    cost: float | None = None
    if cost_raw is not None:
        if isinstance(cost_raw, bool) or not isinstance(cost_raw, (int, float)) or float(cost_raw) <= 0:
            raise ValidationError(f"{ctx}.cost_minutes must be a positive number")
        cost = float(cost_raw)
    return ModelSpec(prov, mod, str(raw.get("effort") or "").strip(), str(raw.get("harness") or "").strip(), cost)


def _parse_per_bug_entry(bval: Any, ctx: str) -> tuple[int, int]:
    if isinstance(bval, bool):
        return (1 if bval else 0, 1)
    if not isinstance(bval, dict):
        raise ValidationError(f"{ctx} must be bool or {{detected, trials}}")
    d_i, t_i = bval.get("detected"), bval.get("trials")
    if isinstance(d_i, bool) or isinstance(t_i, bool) or not isinstance(d_i, int) or not isinstance(t_i, int):
        raise ValidationError(f"{ctx} requires int detected and trials")
    if t_i <= 0 or d_i < 0 or d_i > t_i:
        raise ValidationError(f"{ctx} invalid detected/trials")
    return (d_i, t_i)


def _parse_single_catch_rate(k_str: Any, val: Any, ctx: str) -> tuple[tuple[str, str], CatchRate]:
    if not isinstance(k_str, str) or "/" not in k_str or not isinstance(val, dict):
        raise ValidationError(f"{ctx}[{k_str!r}] must map 'provider/model' to an object")
    prov, mod = k_str.split("/", 1)
    raw_pb = val.get("per_bug")
    per_bug: dict[str, tuple[int, int]] = {}
    if raw_pb is not None:
        if not isinstance(raw_pb, dict) or not raw_pb:
            raise ValidationError(f"{ctx}[{k_str}].per_bug must be a non-empty object")
        per_bug = {str(bid): _parse_per_bug_entry(bv, f"{ctx}[{k_str}].per_bug[{bid}]") for bid, bv in raw_pb.items()}
    if val.get("detected") is None and val.get("planted") is None:
        if not per_bug:
            raise ValidationError(f"{ctx}[{k_str}] requires per_bug or detected/planted")
        d_n, p_n = sum(d for d, _ in per_bug.values()), sum(t for _, t in per_bug.values())
        return (prov.strip(), mod.strip()), CatchRate(d_n, p_n, per_bug)
    d_n, p_n = val.get("detected"), val.get("planted")
    if isinstance(d_n, bool) or isinstance(p_n, bool) or not isinstance(d_n, int) or not isinstance(p_n, int):
        raise ValidationError(f"{ctx}[{k_str}] detected and planted must be integers")
    if p_n <= 0 or d_n < 0 or d_n > p_n:
        raise ValidationError(f"{ctx}[{k_str}] requires 0 <= detected <= planted and planted > 0")
    return (prov.strip(), mod.strip()), CatchRate(d_n, p_n, per_bug)


def parse_catch_rate_map(raw: Any, ctx: str) -> dict[tuple[str, str], CatchRate]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValidationError(f"{ctx} must be an object")
    return dict(_parse_single_catch_rate(k, v, ctx) for k, v in raw.items())


def load_calibration_file(path: str) -> dict[tuple[str, str], CatchRate]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValidationError(f"calibration file {path} must be a JSON object")
    return parse_catch_rate_map(raw.get("models") if isinstance(raw.get("models"), dict) else raw, "calibration.models")


def load_outcomes_file(path: str) -> list[dict[str, Any]]:
    """Load closed-loop review outcomes from a JSON object, JSON list, or JSONL file."""
    text = Path(path).read_text(encoding="utf-8").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    return parsed if isinstance(parsed, list) else [parsed]


def _joint_per_bug_calibration(
    active_keys: list[tuple[str, str]],
    catch_rates: dict[tuple[str, str], CatchRate],
) -> dict[str, Any] | None:
    if not active_keys or any(k not in catch_rates or not catch_rates[k].per_bug for k in active_keys):
        return None
    common = sorted(set.intersection(*(set(catch_rates[k].per_bug) for k in active_keys)))
    if not common:
        return None
    jointly_missed = [bid for bid in common if all(catch_rates[k].per_bug[bid][0] == 0 for k in active_keys)]
    miss_probs = [
        math.prod(1.0 - (float(catch_rates[k].per_bug[bid][0]) / float(catch_rates[k].per_bug[bid][1])) for k in active_keys)
        for bid in common
    ]
    emp_miss = statistics.fmean(miss_probs)
    jeffreys_miss = (sum(miss_probs) + 0.5) / (float(len(common)) + 1.0)
    return {
        "observed": 0, "calibrated": True, "joint_calibration": True,
        "joint_bugs_evaluated": len(common), "jointly_missed_bugs": jointly_missed,
        "empirical_joint_miss_rate": round(emp_miss, 6),
        "jeffreys_joint_miss_prob": round(jeffreys_miss, 6),
        "zero_bug_miss_prob": round(jeffreys_miss, 6),
        "moment_bounds": {"k": len(active_keys), "lower": round(emp_miss, 6), "upper": round(jeffreys_miss, 6)},
        "can_stop": not jointly_missed,
    }


def _parse_commit_masses(raw: Any, vec_name: str, fallback_mass: float) -> dict[str, float]:
    if raw is None:
        return {vec_name: fallback_mass} if fallback_mass > 0.0 else {}
    if isinstance(raw, dict):
        pairs = [(str(cid), _parse_nonneg_float(m, f"vectors[{vec_name}].commit_masses[{cid!r}]")) for cid, m in raw.items()]
        return {cid: m for cid, m in pairs if m is not None and m > 0.0}
    if isinstance(raw, list):
        pairs = [(f"{vec_name}#c{idx}", _parse_nonneg_float(m, f"vectors[{vec_name}].commit_masses[{idx}]")) for idx, m in enumerate(raw)]
        return {cid: m for cid, m in pairs if m is not None and m > 0.0}
    raise ValidationError(f"vectors[{vec_name}].commit_masses must be an object mapping commit_id -> mass")


def _parse_catch_table_cfg(raw_ct: Any, pool_size: int) -> dict[str, Any]:
    if raw_ct is None:
        return build_catch_table("prior", max_k=pool_size)
    if not isinstance(raw_ct, dict):
        raise ValidationError("catch_table must be an object")
    try:
        mbk = {int(k): float(v) for k, v in raw_ct["miss_by_k"].items()} if isinstance(raw_ct.get("miss_by_k"), dict) else None
        return build_catch_table(str(raw_ct.get("provenance") or "prior"), miss_by_k=mbk, anchor=raw_ct.get("anchor"), max_k=pool_size)
    except (ValueError, TypeError) as exc:
        raise ValidationError(f"invalid catch_table: {exc}") from exc


def _parse_config(payload: dict[str, Any]) -> dict[str, Any]:
    if "roles" in payload:
        raise ValidationError("retired top-level 'roles' key is not accepted; use reviewer_pool and worker_model")
    raw_pool = payload.get("reviewer_pool")
    if not isinstance(raw_pool, list) or not raw_pool:
        raise ValidationError("reviewer_pool must be a non-empty list")
    pool = [_parse_model(m, f"reviewer_pool[{i}]") for i, m in enumerate(raw_pool)]
    worker_model = _parse_model(payload["worker_model"], "worker_model") if payload.get("worker_model") is not None else None

    unreach_raw = payload.get("unreachable_models") or []
    if not isinstance(unreach_raw, list):
        raise ValidationError("unreachable_models must be a list")
    unreachable = {
        _parse_model(u, f"unreachable_models[{i}]").key: str(u.get("reason") or "unreachable").strip()
        for i, u in enumerate(unreach_raw)
    }

    target_val = _parse_open_unit_float(payload.get("residual_target"), "residual_target")
    if target_val is None:
        target_val = _parse_open_unit_float(payload.get("miss_risk_target"), "miss_risk_target")
    confidence_alpha = _parse_open_unit_float(payload.get("confidence_alpha"), "confidence_alpha")

    budget_raw = payload.get("budget")
    if budget_raw is not None and not isinstance(budget_raw, dict):
        raise ValidationError("budget must be an object")
    budget_minutes = _parse_nonneg_float(budget_raw.get("budget_minutes"), "budget.budget_minutes") if isinstance(budget_raw, dict) else None
    elapsed_minutes = (_parse_nonneg_float(budget_raw.get("elapsed_minutes"), "budget.elapsed_minutes") or 0.0) if isinstance(budget_raw, dict) else 0.0

    return {
        "target": str(payload.get("target") or "").strip(),
        "pool": pool,
        "pool_by_key": {m.key: m for m in pool},
        "reachable_pool": [m for m in pool if m.key not in unreachable],
        "worker_key": worker_model.key if worker_model else None,
        "unreachable": unreachable,
        "target_val": target_val,
        "confidence_alpha": confidence_alpha,
        "budget_minutes": budget_minutes,
        "elapsed_minutes": elapsed_minutes,
        "catch_table": _parse_catch_table_cfg(payload.get("catch_table"), len(pool)),
    }


def _parse_seams(raw_seams: Any) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], bool]:
    if raw_seams is None:
        return {}, [], False
    if not isinstance(raw_seams, list):
        raise ValidationError("seams must be a list")
    by_name: dict[str, dict[str, Any]] = {}
    outputs: list[dict[str, Any]] = []
    any_failed = False
    for idx, sr in enumerate(raw_seams):
        if not isinstance(sr, dict):
            raise ValidationError(f"seams[{idx}] must be an object")
        sname = _req_str(sr.get("seam") or sr.get("name"), f"seams[{idx}].seam")
        failed_n = int(sr.get("cases_failed", 0) or 0)
        passed = str(sr.get("verdict") or "clean").strip() in ("clean", "exhausted", "obligations_exhausted", "passed") and failed_n == 0 and (sr.get("verified", True) is not False)
        any_failed = any_failed or (not passed)
        entry = {"seam": sname, "verdict": "verified" if passed else "failed", "cases_run": int(sr.get("cases_run", 0) or 0), "cases_failed": failed_n, "landing_blocked": not passed}
        by_name[sname] = entry
        outputs.append(entry)
    return by_name, outputs, any_failed


def _parse_one_vector(vr: Any, idx: int, default_phi: float, seams_by_name: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(vr, dict):
        raise ValidationError(f"vectors[{idx}] must be an object")
    vname = _req_str(vr.get("name"), f"vectors[{idx}].name")
    rk = vr.get("risk")
    if isinstance(rk, bool) or not isinstance(rk, (int, float)) or not math.isfinite(float(rk)) or not (0.0 <= float(rk) < 1.0):
        raise ValidationError(f"vectors[{vname}].risk must be a finite number in [0.0, 1.0), got {rk!r}")
    risk_f = float(rk)
    phi_f = _parse_nonneg_float(vr.get("phi", default_phi), f"vectors[{vname}].phi") or 0.0
    tgt = vr.get("target")
    if tgt is not None and str(tgt) not in VALID_RISK_TARGETS:
        raise ValidationError(f"vectors[{vname}].target must be one of {VALID_RISK_TARGETS}")
    raw_mass = _parse_nonneg_float(vr.get("mass"), f"vectors[{vname}].mass")
    base_mass = raw_mass if raw_mass is not None else invert_risk_to_mass(risk_f, phi_f)
    cm = _parse_commit_masses(vr.get("commit_masses"), vname, base_mass)
    eff_mass = sum(cm.values()) if cm else base_mass
    gap_mass = _parse_nonneg_float(vr.get("gap_mass"), f"vectors[{vname}].gap_mass") or 0.0
    exp_raw = vr.get("exposure")
    alloc_w = float(exp_raw) if (exp_raw is not None and not isinstance(exp_raw, bool) and float(exp_raw) > 0) else eff_mass
    linked_seams = [str(s) for s in (vr.get("seams") or [])]
    missing_seams = [s for s in linked_seams if s not in seams_by_name]
    if missing_seams:
        raise ValidationError(f"vectors[{vname}] references unknown seam {missing_seams[0]!r}")
    return {
        "name": vname, "risk": risk_f, "phi": phi_f, "mass": eff_mass, "gap_mass": gap_mass,
        "alloc_weight": alloc_w, "commit_masses": cm, "target": str(tgt) if tgt is not None else None,
        "finder_checks": vr.get("finder_checks") if isinstance(vr.get("finder_checks"), dict) else None,
        "kind_scope_upper_bound": bool(vr.get("kind_scope_upper_bound", False)), "seams": linked_seams,
    }


def _parse_vectors_and_reviews(
    payload: dict[str, Any],
    pool_by_key: dict[tuple[str, str], ModelSpec],
    seams_by_name: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    raw_vecs = payload.get("vectors")
    if not isinstance(raw_vecs, list):
        raise ValidationError("vectors must be a list")
    default_phi = float(payload.get("phi", 0.0) or 0.0)
    vectors = [_parse_one_vector(vr, idx, default_phi, seams_by_name) for idx, vr in enumerate(raw_vecs)]
    if len({v["name"] for v in vectors}) != len(vectors):
        raise ValidationError("duplicate vector name in vectors")

    for idx, eq in enumerate(payload.get("equivalence_checks") or []):
        if not isinstance(eq, dict):
            raise ValidationError(f"equivalence_checks[{idx}] must be an object")
        _req_str(eq.get("vector"), f"equivalence_checks[{idx}].vector")
        _req_str(eq.get("root_cause"), f"equivalence_checks[{idx}].root_cause")
        if not isinstance(eq.get("fix_verified"), bool):
            raise ValidationError(f"equivalence_checks[{idx}].fix_verified must be a boolean")

    raw_revs = payload.get("reviews") or []
    if not isinstance(raw_revs, list):
        raise ValidationError("reviews must be a list")
    revs_by_vec: dict[str, list[dict[str, Any]]] = {v["name"]: [] for v in vectors}
    for idx, rr in enumerate(raw_revs):
        if not isinstance(rr, dict):
            raise ValidationError(f"reviews[{idx}] must be an object")
        vname = _req_str(rr.get("vector"), f"reviews[{idx}].vector")
        if vname not in revs_by_vec:
            raise ValidationError(f"reviews[{idx}] references unknown vector {vname!r}")
        ms = _parse_model(rr, f"reviews[{idx}]")
        if ms.key not in pool_by_key:
            raise ValidationError(f"reviews[{idx}] uses unapproved model {ms.label} not in reviewer_pool")
        ver = rr.get("verified")
        if not isinstance(ver, list) or not all(isinstance(x, str) and x.strip() for x in ver):
            raise ValidationError(f"reviews[{idx}].verified must be a list of non-empty bug IDs")
        revs_by_vec[vname].append({"model": ms, "verified": sorted({x.strip() for x in ver}), "dropped": int(rr.get("dropped", 0) or 0)})
    return vectors, revs_by_vec


def _expert_share_for_outcome(vec: dict[str, Any], expert: str, n_vecs: int) -> float:
    unif = 1.0 / float(max(1, n_vecs))
    if expert == "unif":
        return unif
    if expert == "hist":
        raw = vec.get("hist_share", vec.get("share"))
        return float(raw) if isinstance(raw, (int, float)) and not isinstance(raw, bool) and float(raw) > 0.0 else _EPS
    raw_g = vec.get("gap_share")
    return float(raw_g) if isinstance(raw_g, (int, float)) and not isinstance(raw_g, bool) and float(raw_g) > 0.0 else unif


def _outcome_expert_log_likelihood(
    vecs: list[dict[str, Any]],
    expert: str,
    catch_table: dict[str, Any],
) -> float:
    """Detection-debiased log-likelihood: conditions share on c(k) = 1 - M_alloc(k) to prevent confirmation bias."""
    n_v = len(vecs)
    weighted = [
        _expert_share_for_outcome(v, expert, n_v)
        * max(_EPS, 1.0 - catch_miss_at(catch_table, int(v.get("reviewers_completed", 0) or 0))[1])
        for v in vecs
    ]
    z = sum(weighted)
    if z <= 0.0:
        return 0.0
    return sum(
        int(v.get("observed_blockers", 0) or 0) * math.log(max(_EPS, min(1.0 - _EPS, w_v / z)))
        for v, w_v in zip(vecs, weighted)
        if int(v.get("observed_blockers", 0) or 0) > 0
    )


def _fit_expert_weights(
    outcomes: list[dict[str, Any]],
    experts: tuple[str, ...],
    catch_table: dict[str, Any],
) -> dict[str, Any]:
    """Dynamic switching-expert weights via debiased Bayes + parameter-free Decreasing Share alpha_t = 1/(t+1)."""
    n_exp = len(experts)
    weights = {e: 1.0 / float(n_exp) for e in experts}
    cum_loss = {e: 0.0 for e in experts}
    evaluated = 0
    for rec in outcomes:
        vecs = rec.get("vectors") if isinstance(rec, dict) and isinstance(rec.get("vectors"), list) else []
        active = [v for v in vecs if isinstance(v, dict) and int(v.get("reviewers_completed", 0) or 0) > 0]
        if not active or sum(int(v.get("observed_blockers", 0) or 0) for v in active) <= 0:
            continue
        evaluated += 1
        lls = {e: _outcome_expert_log_likelihood(active, e, catch_table) for e in experts}
        for e in experts:
            cum_loss[e] += -lls[e]
        log_p = {e: math.log(max(_EPS, weights[e])) + lls[e] for e in experts}
        m_lp = max(log_p.values())
        z = m_lp + math.log(sum(math.exp(v - m_lp) for v in log_p.values()))
        alpha_t = 1.0 / float(evaluated + 1)
        weights = {e: (1.0 - alpha_t) * math.exp(log_p[e] - z) + alpha_t / float(n_exp) for e in experts}

    other_losses = [cum_loss[e] for e in experts if e != "hist"]
    return {
        "weights": {e: round(weights[e], 6) for e in experts},
        "dynamic_gap_share": round(sum(weights[e] for e in experts if e != "hist"), 6),
        "outcomes_evaluated": evaluated,
        "cumulative_debiased_log_loss": {e: round(cum_loss[e], 6) for e in experts},
        "miscalibrated_on_gaps": bool(evaluated > 0 and other_losses and cum_loss["hist"] > min(other_losses) + _SQRT_EPS),
        "_raw_weights": weights,
    }


def _pick_models(
    reachable_pool: list[ModelSpec],
    used_keys: set[tuple[str, str]],
    used_providers: set[str],
    worker_key: tuple[str, str] | None,
    count: int,
) -> list[ModelSpec]:
    avail = [m for m in reachable_pool if m.key not in used_keys]
    picked: list[ModelSpec] = []
    seen_prov = set(used_providers)
    while len(picked) < count and avail:
        avail.sort(key=lambda m: (1 if m.key == worker_key else 0, 1 if m.provider in seen_prov else 0, m.cost_minutes or 1.0, m.provider, m.model))
        chosen = avail.pop(0)
        picked.append(chosen)
        seen_prov.add(chosen.provider)
    return picked


def _effective_vector_shares(
    risky_open: list[dict[str, Any]],
    raw_weights: dict[str, float],
) -> tuple[dict[str, float], dict[str, bool]]:
    """Level-invariant effective allocation shares blending historical, gap, and uniform experts."""
    n_open = len(risky_open)
    tot_h = sum(vs["spec"]["alloc_weight"] for vs in risky_open)
    tot_g = sum(vs["spec"]["gap_mass"] for vs in risky_open)
    w_h = raw_weights.get("hist", 0.0)
    w_g = raw_weights.get("gap", 0.0)
    w_u = raw_weights.get("unif", 0.0)
    eff: dict[str, float] = {}
    gap_driven: dict[str, bool] = {}
    for vs in risky_open:
        vn = vs["spec"]["name"]
        sh = (vs["spec"]["alloc_weight"] / tot_h) if tot_h > 0.0 else (1.0 / float(n_open))
        sg = (vs["spec"]["gap_mass"] / tot_g) if tot_g > 0.0 else 0.0
        su = 1.0 / float(n_open)
        hist_part = w_h * sh
        gap_part = w_g * sg + w_u * su
        eff[vn] = hist_part + gap_part
        gap_driven[vn] = gap_part > hist_part + _SQRT_EPS
    return eff, gap_driven


def _best_vector_marginal(
    risky_open: list[dict[str, Any]],
    eff_shares: dict[str, float],
    counts: dict[str, int],
    pool_len: int,
    catch_table: dict[str, Any],
    unit_cost: float,
) -> str | None:
    best_key: tuple[float, int] | None = None
    best_name: str | None = None
    for vs in risky_open:
        vn = vs["spec"]["name"]
        if counts[vn] >= pool_len:
            continue
        _, m_cur, _, _ = catch_miss_at(catch_table, counts[vn])
        _, m_nxt, _, _ = catch_miss_at(catch_table, counts[vn] + 1)
        gain = (eff_shares[vn] * max(0.0, m_cur - m_nxt)) / unit_cost
        cand = (gain, -counts[vn])
        if gain > _SQRT_EPS and (best_key is None or cand[0] > best_key[0] + _SQRT_EPS * max(1.0, best_key[0]) or (abs(cand[0] - best_key[0]) <= _SQRT_EPS * max(1.0, best_key[0]) and cand[1] > best_key[1])):
            best_key, best_name = cand, vn
    return best_name


def _allocate_wave_extra(
    vec_state: list[dict[str, Any]],
    reachable_pool: list[ModelSpec],
    catch_table: dict[str, Any],
    budget_minutes: float | None,
    elapsed_minutes: float,
    outcomes: list[dict[str, Any]],
) -> tuple[dict[str, int], dict[str, str], dict[str, Any]]:
    """Wave-bounded, level-invariant allocation with dynamic switching gap exploration (zero fixed share)."""
    counts = {vs["spec"]["name"]: len(vs["distinct_runs"]) for vs in vec_state}
    extra = {vs["spec"]["name"]: 0 for vs in vec_state}
    brief_modes = {vs["spec"]["name"]: "standard" for vs in vec_state}
    risky_open = [vs for vs in vec_state if vs["spec"]["risk"] > 0.0 and not vs["seam_backed"]]
    has_gap = any(vs["spec"]["gap_mass"] > 0.0 for vs in risky_open)
    experts: tuple[str, ...] = ("hist", "gap", "unif") if has_gap else ("hist", "unif")
    expert_info = _fit_expert_weights(outcomes, experts, catch_table)
    if not risky_open or not reachable_pool:
        return extra, brief_modes, expert_info

    eff_shares, gap_driven = _effective_vector_shares(risky_open, expert_info["_raw_weights"])
    unit_cost = statistics.fmean([m.cost_minutes for m in reachable_pool if m.cost_minutes is not None] or [1.0])
    wave_cap = 2 * len(risky_open)
    if budget_minutes is not None:
        rem = max(0.0, budget_minutes - elapsed_minutes)
        slot_budget = min(wave_cap, int((rem + _SQRT_EPS * max(1.0, unit_cost)) // unit_cost))
    else:
        slot_budget = wave_cap

    unreviewed = [vs["spec"]["name"] for vs in risky_open if counts[vs["spec"]["name"]] == 0]
    for vn in unreviewed:
        counts[vn] += 1
        extra[vn] += 1
        if gap_driven[vn]:
            brief_modes[vn] = "gap_brief"
    slots_left = max(0, slot_budget - len(unreviewed))

    while slots_left > 0:
        best_name = _best_vector_marginal(risky_open, eff_shares, counts, len(reachable_pool), catch_table, unit_cost)
        if best_name is None:
            break
        counts[best_name] += 1
        extra[best_name] += 1
        if gap_driven[best_name]:
            brief_modes[best_name] = "gap_brief"
        slots_left -= 1
    return extra, brief_modes, expert_info


def _capture_recapture_summary(runs: list[dict[str, Any]], alpha: float | None) -> tuple[dict[str, Any], bool]:
    k = len(runs)
    if k == 2:
        s1, s2 = set(runs[0]["verified"]), set(runs[1]["verified"])
        return chapman_estimate(len(s1), len(s2), len(s1 & s2), alpha=alpha), (s1 == s2)
    bug_counts: dict[str, int] = {}
    for b in (bug for r in runs for bug in r["verified"]):
        bug_counts[b] = bug_counts.get(b, 0) + 1
    freqs = [sum(1 for c in bug_counts.values() if c == j) for j in range(1, k + 1)]
    return jackknife_mh_estimate(freqs, k, alpha=alpha), (freqs[0] == 0)


def _decide_positive_bugs(
    vs: dict[str, Any],
    cfg: dict[str, Any],
    planned_extra: int,
) -> tuple[str, str, str, bool, dict[str, Any] | None, list[ModelSpec]]:
    runs = vs["distinct_runs"]
    unused = [m for m in cfg["reachable_pool"] if m.key not in vs["seen_keys"]]
    if len(runs) < 2:
        if unused:
            return "continue", "continue", "second_independent_model_required", True, None, _pick_models(cfg["reachable_pool"], vs["seen_keys"], vs["used_providers"], cfg["worker_key"], max(1, planned_extra))
        if cfg["unreachable"]:
            return "flag", "pool_exhausted", "remaining_pool_models_unreachable", True, None, []
        return "stop", "fix_and_rereview", "single_model_pool_fix_and_rereview", True, None, []

    est, zero_singletons = _capture_recapture_summary(runs, cfg["confidence_alpha"])
    if est["can_stop"]:
        return "stop", "fix_and_rereview", "saturated_observable_class", True, est, []
    if unused:
        reason = "unanimous_small_count_needs_capture_recapture_check" if zero_singletons else "models_still_finding_new_bugs"
        return "continue", "continue", reason, True, est, _pick_models(cfg["reachable_pool"], vs["seen_keys"], vs["used_providers"], cfg["worker_key"], 1)
    if cfg["unreachable"]:
        return "flag", "pool_exhausted", "remaining_pool_models_unreachable", True, est, []
    if zero_singletons:
        return "stop", "fix_and_rereview", "all_models_unanimous_fix_and_rereview", True, est, []
    return "flag", "pool_exhausted", "pool_exhausted_with_open_singletons", True, est, []


def _decide_zero_bugs(
    vs: dict[str, Any],
    cfg: dict[str, Any],
    rb: dict[str, Any],
    catch_rates: dict[tuple[str, str], CatchRate],
    planned_extra: int,
) -> tuple[str, str, str, bool, dict[str, Any] | None, list[ModelSpec]]:
    runs = vs["distinct_runs"]
    k = len(runs)
    unused = [m for m in cfg["reachable_pool"] if m.key not in vs["seen_keys"]]
    budget_done = cfg["budget_minutes"] is not None and (cfg["elapsed_minutes"] >= cfg["budget_minutes"])

    cal_est = _joint_per_bug_calibration([r["model"].key for r in runs], catch_rates)
    if cal_est is not None and cfg["target_val"] is not None:
        cal_est["can_stop"] = (not cal_est["jointly_missed_bugs"]) and (cal_est["jeffreys_joint_miss_prob"] <= cfg["target_val"])

    if k == 0:
        if unused and not budget_done:
            want = max(1, planned_extra)
            return "continue", "continue", "initial_mass_allocation", False, None, _pick_models(cfg["reachable_pool"], vs["seen_keys"], vs["used_providers"], cfg["worker_key"], want)
        return "flag", ("budget_exhausted" if budget_done else "pool_exhausted"), "no_review_completed", True, None, []
    if cal_est is not None:
        if cal_est["can_stop"] and k >= 2:
            return "stop", "clean_stop", "calibrated_zero_shared_blind_spots", False, cal_est, []
        if unused and not budget_done:
            reason = "shared_blind_spot_detected" if cal_est["jointly_missed_bugs"] else "calibration_target_unmet"
            return "continue", "continue", reason, False, cal_est, _pick_models(cfg["reachable_pool"], vs["seen_keys"], vs["used_providers"], cfg["worker_key"], 1)
        reason = "shared_blind_spot_unclosed" if cal_est["jointly_missed_bugs"] else "remaining_pool_models_unreachable"
        return "flag", "pool_exhausted", reason, True, cal_est, []
    if budget_done:
        return ("flag" if k < 2 else "stop"), "budget_exhausted", "budget_exhausted", (k < 2), None, []
    if k < 2 and unused:
        return "continue", "continue", "second_independent_model_required", False, None, _pick_models(cfg["reachable_pool"], vs["seen_keys"], vs["used_providers"], cfg["worker_key"], 1)
    if k < 2 and cfg["unreachable"]:
        return "flag", "pool_exhausted", "remaining_pool_models_unreachable", True, None, []
    if cfg["target_val"] is not None and rb["residual_risk"] is not None and rb["residual_risk"] <= cfg["target_val"]:
        return "stop", "clean_stop", "residual_below_target", False, None, []
    if cfg["target_val"] is not None and unused:
        return "continue", "continue", "target_not_yet_met", False, None, _pick_models(cfg["reachable_pool"], vs["seen_keys"], vs["used_providers"], cfg["worker_key"], 1)
    return "stop", "clean_stop", "independent_models_clean", False, None, []


def _build_vector_state(v: dict[str, Any], runs: list[dict[str, Any]], seams_by_name: dict[str, dict[str, Any]]) -> dict[str, Any]:
    seen_keys: set[tuple[str, str]] = set()
    distinct_runs: list[dict[str, Any]] = []
    violations: list[str] = []
    for r in runs:
        if r["model"].key in seen_keys:
            violations.append(f"duplicate_model_on_vector:{r['model'].label}")
            continue
        seen_keys.add(r["model"].key)
        distinct_runs.append(r)
    return {
        "spec": v,
        "distinct_runs": distinct_runs,
        "seen_keys": seen_keys,
        "used_providers": {r["model"].provider for r in distinct_runs},
        "all_bugs": sorted({b for r in distinct_runs for b in r["verified"]}),
        "violations": violations,
        "seam_backed": bool(v["seams"]) and all(seams_by_name[s]["verdict"] == "verified" for s in v["seams"]),
    }


def _decide_vector_outcome(
    vs: dict[str, Any],
    cfg: dict[str, Any],
    rb: dict[str, Any],
    catch_rates: dict[tuple[str, str], CatchRate],
    planned_extra: int,
    violations: list[str],
) -> tuple[str, str, str, bool, dict[str, Any] | None, list[ModelSpec]]:
    v, runs = vs["spec"], vs["distinct_runs"]
    k, D = len(runs), len(vs["all_bugs"])
    non_worker_runs = [r for r in runs if cfg["worker_key"] is None or r["model"].key != cfg["worker_key"]]
    non_worker_avail = [m for m in cfg["reachable_pool"] if m.key not in vs["seen_keys"] and (cfg["worker_key"] is None or m.key != cfg["worker_key"])]

    if k > 0 and not non_worker_runs and non_worker_avail:
        violations.append("worker_model_only")
        return "continue", "continue", "non_worker_model_required", False, None, _pick_models(cfg["reachable_pool"], vs["seen_keys"], vs["used_providers"], cfg["worker_key"], 1)
    if (v["risk"] == 0.0 or vs["seam_backed"]) and D == 0 and k >= 1:
        reason = "seam_verified_single_clean" if vs["seam_backed"] else "zero_risk_single_clean"
        return "stop", "clean_stop", reason, False, None, []
    if (v["risk"] == 0.0 or vs["seam_backed"]) and D == 0:
        return "continue", "continue", "needs_initial_review", False, None, _pick_models(cfg["reachable_pool"], vs["seen_keys"], vs["used_providers"], cfg["worker_key"], 1)
    if D > 0:
        return _decide_positive_bugs(vs, cfg, planned_extra)
    return _decide_zero_bugs(vs, cfg, rb, catch_rates, planned_extra)


def _evaluate_one_vector(
    vs: dict[str, Any],
    cfg: dict[str, Any],
    catch_rates: dict[tuple[str, str], CatchRate],
    planned_extra: int,
    brief_mode: str,
    total_mass: float,
    total_gap: float,
) -> dict[str, Any]:
    v, runs = vs["spec"], vs["distinct_runs"]
    k, D = len(runs), len(vs["all_bugs"])
    violations = list(vs["violations"])
    rb = residual_risk_with_bracket(v["commit_masses"], v["phi"], k, cfg["catch_table"])
    action, verdict, reason, blocked, est, next_models = _decide_vector_outcome(vs, cfg, rb, catch_rates, planned_extra, violations)

    share = round(v["mass"] / total_mass, 6) if total_mass > 0.0 else 0.0
    gap_share = round(v["gap_mass"] / total_gap, 6) if total_gap > 0.0 else 0.0
    return {
        "name": v["name"], "risk": round_risk(v["risk"]), "mass": round(v["mass"], 6), "share": share,
        "gap_mass": round(v["gap_mass"], 6), "gap_share": gap_share, "brief_mode": brief_mode,
        "phi": round(v["phi"], 6), "target": v["target"], "finder_checks": v["finder_checks"],
        "kind_scope_upper_bound": v["kind_scope_upper_bound"], **rb,
        "reviewers_completed": k, "observed_blockers": D, "action": action, "verdict": verdict,
        "reason": reason, "landing_blocked": blocked, "rule_violations": violations,
        "estimate": est, "plain_range": format_plain_range(est),
        "next_models": [m.to_dict() for m in next_models],
    }


def evaluate_ledger(
    payload: dict[str, Any],
    *,
    external_catch_rates: dict[tuple[str, str], CatchRate] | None = None,
    external_outcomes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Evaluate structural gates, capture-recapture saturation, and dynamic gap-hedged reviewer allocation."""
    if not isinstance(payload, dict):
        raise ValidationError("ledger input must be a JSON object")
    cfg = _parse_config(payload)
    catch_rates = {**(external_catch_rates or {}), **parse_catch_rate_map(payload.get("model_catch_rates"), "model_catch_rates")}
    seams_by_name, seam_outputs, any_seam_failed = _parse_seams(payload.get("seams"))
    vectors, revs_by_vec = _parse_vectors_and_reviews(payload, cfg["pool_by_key"], seams_by_name)
    raw_outcomes = payload.get("past_review_outcomes") or []
    if not isinstance(raw_outcomes, list):
        raise ValidationError("past_review_outcomes must be a list")
    outcomes = [*(external_outcomes or []), *raw_outcomes]

    vec_state = [_build_vector_state(v, revs_by_vec[v["name"]], seams_by_name) for v in vectors]
    planned_extra, brief_modes, expert_info = _allocate_wave_extra(
        vec_state, cfg["reachable_pool"], cfg["catch_table"], cfg["budget_minutes"], cfg["elapsed_minutes"], outcomes,
    )
    phi_global = vectors[0]["phi"] if vectors else 0.0
    total_mass = sum(v["mass"] for v in vectors)
    total_gap = sum(v["gap_mass"] for v in vectors)
    change_risk = compose_change_risk([v["commit_masses"] for v in vectors], phi_global)

    vec_outputs = [
        _evaluate_one_vector(vs, cfg, catch_rates, planned_extra[vs["spec"]["name"]], brief_modes[vs["spec"]["name"]], total_mass, total_gap)
        for vs in vec_state
    ]
    allocated_by_vec = {vo["name"]: vo["next_models"] for vo in vec_outputs}
    next_actions = [
        "{}: dispatch {} ({}{})".format(
            vo["name"],
            ", ".join("{}/{}".format(m["provider"], m["model"]) for m in vo["next_models"]),
            vo["reason"],
            "; gap_brief" if vo["brief_mode"] == "gap_brief" else "",
        )
        for vo in vec_outputs
        if vo["action"] == "continue"
    ]
    lanes_lines = [
        f"ledger: {vo['name']} risk={vo['risk']:.4f} share={vo['share']:.4f} k={vo['reviewers_completed']} D={vo['observed_blockers']} action={vo['action']} reason={vo['reason']}"
        for vo in vec_outputs
    ]
    any_flag = any(vo["action"] == "flag" for vo in vec_outputs)
    any_continue = any(vo["action"] == "continue" for vo in vec_outputs)
    any_blocked = any_seam_failed or any(vo["landing_blocked"] for vo in vec_outputs)

    ch_rb = change_residual_risk_with_bracket([(vs["spec"]["commit_masses"], len(vs["distinct_runs"])) for vs in vec_state], phi_global, cfg["catch_table"])
    overall = "flagged" if (any_flag or any_seam_failed) else ("continue" if any_continue else "complete")
    unit_cost = statistics.fmean([m.cost_minutes for m in cfg["reachable_pool"] if m.cost_minutes is not None] or [1.0])
    planned_models = [m for ms in allocated_by_vec.values() for m in ms]
    planned_cost = round(sum(float(m.get("cost_minutes") or unit_cost) for m in planned_models), 6)
    rem_budget = None if cfg["budget_minutes"] is None else round(max(0.0, cfg["budget_minutes"] - cfg["elapsed_minutes"]), 6)
    budget_exceeded = bool(rem_budget is not None and planned_cost > rem_budget + _SQRT_EPS * max(1.0, rem_budget))
    budget_overrun = round(max(0.0, planned_cost - rem_budget), 6) if rem_budget is not None else 0.0
    ch_risk_rounded = round_risk(change_risk)
    cal_public = {k: v for k, v in expert_info.items() if not k.startswith("_")}
    outcome_record = {
        "target": cfg["target"],
        "vectors": [
            {
                "name": vo["name"],
                "hist_share": vo["share"],
                "gap_share": vo["gap_share"],
                "reviewers_completed": vo["reviewers_completed"],
                "observed_blockers": vo["observed_blockers"],
            }
            for vo in vec_outputs
        ],
    }
    return {
        "target": cfg["target"], "overall": overall, "landing_blocked": any_blocked,
        "change_mass": round(total_mass, 6), "change_risk": ch_risk_rounded, **ch_rb,
        "catch_table": {k: v for k, v in cfg["catch_table"].items() if not k.startswith("_")},
        "scorer_calibration": cal_public,
        "outcome_record": outcome_record,
        "risk_allocation": {
            "decision_mode": "target_threshold" if cfg["target_val"] is not None else "budget_minimization",
            "allocated_models_by_vector": allocated_by_vec,
            "brief_modes_by_vector": {vo["name"]: vo["brief_mode"] for vo in vec_outputs},
            "expert_weights": cal_public["weights"],
            "dynamic_gap_share": cal_public["dynamic_gap_share"],
            "planned_reviewers": len(planned_models),
            "planned_cost": planned_cost,
            "remaining_budget": rem_budget,
            "budget_exceeded": budget_exceeded,
            "budget_overrun": budget_overrun,
            "change_risk": ch_risk_rounded,
            **ch_rb,
        },
        "seams": seam_outputs, "vectors": vec_outputs, "next_actions": next_actions,
        "could_not_test": [{"model": f"{mk[0]}/{mk[1]}", "reason": r} for mk, r in sorted(cfg["unreachable"].items())],
        "lanes_log_lines": lanes_lines,
    }
