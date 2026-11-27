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
    compose_vector_risk,
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


def _parse_pos_int(val: Any, name: str) -> int | None:
    if val is None:
        return None
    if isinstance(val, bool) or not isinstance(val, int) or val < 1:
        raise ValidationError(f"{name} must be an integer >= 1")
    return int(val)


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


def _read_receipt_json(path: Path) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if isinstance(parsed, dict):
        return [parsed]
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    return []


def _collect_receipt_files(raw_path: str) -> list[Path]:
    target = Path(raw_path).expanduser()
    if target.is_file():
        return [target]
    if not target.is_dir():
        raise ValidationError(f"receipts path not found: {target}")
    found = {p.resolve() for p in target.rglob("*.receipt.json") if p.is_file()}
    found.update(
        p.resolve()
        for p in target.iterdir()
        if p.is_file() and p.name.endswith(".json") and not p.name.endswith(".job.json") and not p.name.startswith(".")
    )
    return sorted(found)


def load_dispatch_receipts(paths: list[str]) -> list[dict[str, Any]]:
    """Load astack-dispatch receipt/state JSON objects from files or directories."""
    receipts: list[dict[str, Any]] = []
    for raw_path in paths:
        for file_path in _collect_receipt_files(raw_path):
            receipts.extend(_read_receipt_json(file_path))
    return receipts


_BLOCKED_NOTE_MARKERS = (
    "content_filter",
    "content filter",
    "usage policy",
    "usage policies",
    "safety policy",
    "safety filter",
    "invalid_prompt",
    "potentially violating",
    "violates our",
    "moderation",
    "policy",
    "blocked",
)


def _receipt_failure_status(rec: dict[str, Any]) -> tuple[str, str] | None:
    state = str(rec.get("state") or "").strip().lower()
    timed_out = bool(rec.get("timed_out", False))
    exit_code = rec.get("exit_code")
    note = str(rec.get("note") or rec.get("reason") or "").strip()
    if state == "running":
        return None
    if timed_out or state == "timed_out":
        return "timed_out", note or "dispatch_timed_out"
    low = f"{state} {note}".lower()
    if state == "blocked" or any(tok in low for tok in _BLOCKED_NOTE_MARKERS):
        return "blocked", note or "dispatch_blocked"
    if state in ("failed", "killed", "unreachable") or (isinstance(exit_code, int) and not isinstance(exit_code, bool) and exit_code != 0):
        return ("unreachable" if state == "unreachable" else "failed"), note or f"dispatch_{state or f'exit_{exit_code}'}"
    return None


def _promote_blocked_models(
    cfg: dict[str, Any],
    failed_by_vec: dict[str, list[dict[str, Any]]],
) -> None:
    """Treat blocked/unreachable model failures (e.g. content filters) as globally unreachable across all vectors."""
    blocked = [
        f for entries in failed_by_vec.values() for f in entries
        if f["status"] in ("blocked", "unreachable") and f["model"].key not in cfg["unreachable"]
    ]
    if not blocked:
        return
    for f in blocked:
        cfg["unreachable"].setdefault(f["model"].key, f"{f['status']}: {f['reason']}")
    cfg["reachable_pool"] = [m for m in cfg["pool"] if m.key not in cfg["unreachable"]]


def _validate_no_contradictory_reviews(
    revs_by_vec: dict[str, list[dict[str, Any]]],
    failed_by_vec: dict[str, list[dict[str, Any]]],
) -> None:
    """Reject contradictory payloads recording the same model as both completed and failed on one vector."""
    for vname, completed in revs_by_vec.items():
        completed_keys = {r["model"].key for r in completed}
        conflicts = [f["model"].label for f in failed_by_vec.get(vname, ()) if f["model"].key in completed_keys]
        if conflicts:
            raise ValidationError(f"contradictory status for {conflicts[0]} on vector {vname!r}: recorded as both completed and failed")


def _merge_receipt_failures(
    receipts: list[dict[str, Any]],
    revs_by_vec: dict[str, list[dict[str, Any]]],
    failed_by_vec: dict[str, list[dict[str, Any]]],
    pool_by_key: dict[tuple[str, str], ModelSpec],
) -> None:
    """Ingest failed/blocked astack-dispatch reviewer receipts so leads cannot forget to log model failures."""
    latest: dict[tuple[str, tuple[str, str]], tuple[str, dict[str, Any]]] = {}
    for rec in receipts:
        if not isinstance(rec, dict):
            continue
        role = str(rec.get("role") or "reviewer").strip().lower()
        vname = str(rec.get("vector") or "").strip()
        key = (str(rec.get("provider") or "").strip(), str(rec.get("model") or "").strip())
        if role != "reviewer" or vname not in revs_by_vec or key not in pool_by_key:
            continue
        stamp = str(rec.get("finished_at") or rec.get("timestamp") or rec.get("started_at") or "")
        slot = (vname, key)
        if slot not in latest or stamp >= latest[slot][0]:
            latest[slot] = (stamp, rec)

    for (vname, key), (_, rec) in latest.items():
        if any(r["model"].key == key for r in revs_by_vec[vname]):
            continue
        fail_info = _receipt_failure_status(rec)
        if fail_info is None:
            continue
        status, reason = fail_info
        bm = str(rec.get("brief_mode") or "").strip()
        failed_by_vec[vname].append({"model": pool_by_key[key], "status": status, "reason": reason, "brief_mode": bm})


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
    wave_budget_minutes = _parse_nonneg_float(budget_raw.get("wave_budget_minutes"), "budget.wave_budget_minutes") if isinstance(budget_raw, dict) else None
    max_budget_minutes = _parse_nonneg_float(budget_raw.get("max_budget_minutes"), "budget.max_budget_minutes") if isinstance(budget_raw, dict) else None
    max_wave_reviewers = _parse_pos_int(budget_raw.get("max_wave_reviewers"), "budget.max_wave_reviewers") if isinstance(budget_raw, dict) else None

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
        "wave_budget_minutes": wave_budget_minutes,
        "max_budget_minutes": max_budget_minutes,
        "max_wave_reviewers": max_wave_reviewers,
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
    raw_known = vr.get("known_blockers") or []
    if not isinstance(raw_known, list) or not all(isinstance(x, str) and x.strip() for x in raw_known):
        raise ValidationError(f"vectors[{vname}].known_blockers must be a list of non-empty bug IDs")
    return {
        "name": vname, "risk": risk_f, "phi": phi_f, "mass": eff_mass, "gap_mass": gap_mass,
        "alloc_weight": alloc_w, "commit_masses": cm, "target": str(tgt) if tgt is not None else None,
        "finder_checks": vr.get("finder_checks") if isinstance(vr.get("finder_checks"), dict) else None,
        "kind_scope_upper_bound": bool(vr.get("kind_scope_upper_bound", False)),
        "seams": linked_seams, "known_blockers": sorted({x.strip() for x in raw_known}),
    }


_FAILED_REVIEW_STATUSES = frozenset({"failed", "blocked", "timed_out", "unreachable"})


def _parse_failed_entry(
    raw: Any,
    ctx: str,
    failed_by_vec: dict[str, list[dict[str, Any]]],
    pool_by_key: dict[tuple[str, str], ModelSpec],
) -> None:
    if not isinstance(raw, dict):
        raise ValidationError(f"{ctx} must be an object")
    vname = _req_str(raw.get("vector"), f"{ctx}.vector")
    if vname not in failed_by_vec:
        raise ValidationError(f"{ctx} references unknown vector {vname!r}")
    ms = _parse_model(raw, ctx)
    if ms.key not in pool_by_key:
        raise ValidationError(f"{ctx} uses unapproved model {ms.label} not in reviewer_pool")
    status = str(raw.get("status") or "failed").strip().lower()
    if status not in _FAILED_REVIEW_STATUSES:
        raise ValidationError(f"{ctx}.status must be one of {sorted(_FAILED_REVIEW_STATUSES)}")
    reason = str(raw.get("reason") or status).strip()
    bm = str(raw.get("brief_mode") or "").strip()
    failed_by_vec[vname].append({"model": ms, "status": status, "reason": reason, "brief_mode": bm})


def _parse_one_review_entry(
    rr: Any,
    idx: int,
    revs_by_vec: dict[str, list[dict[str, Any]]],
    failed_by_vec: dict[str, list[dict[str, Any]]],
    pool_by_key: dict[tuple[str, str], ModelSpec],
) -> None:
    if not isinstance(rr, dict):
        raise ValidationError(f"reviews[{idx}] must be an object")
    status = str(rr.get("status") or "completed").strip().lower()
    if status in _FAILED_REVIEW_STATUSES:
        _parse_failed_entry(rr, f"reviews[{idx}]", failed_by_vec, pool_by_key)
        return
    if status != "completed":
        raise ValidationError(f"reviews[{idx}].status must be 'completed' or one of {sorted(_FAILED_REVIEW_STATUSES)}")
    vname = _req_str(rr.get("vector"), f"reviews[{idx}].vector")
    if vname not in revs_by_vec:
        raise ValidationError(f"reviews[{idx}] references unknown vector {vname!r}")
    ms = _parse_model(rr, f"reviews[{idx}]")
    if ms.key not in pool_by_key:
        raise ValidationError(f"reviews[{idx}] uses unapproved model {ms.label} not in reviewer_pool")
    ver = rr.get("verified")
    if not isinstance(ver, list) or not all(isinstance(x, str) and x.strip() for x in ver):
        raise ValidationError(f"reviews[{idx}].verified must be a list of non-empty bug IDs")
    bm = str(rr.get("brief_mode") or "").strip()
    revs_by_vec[vname].append({"model": ms, "verified": sorted({x.strip() for x in ver}), "dropped": int(rr.get("dropped", 0) or 0), "brief_mode": bm})


def _parse_vectors_and_reviews(
    payload: dict[str, Any],
    pool_by_key: dict[tuple[str, str], ModelSpec],
    seams_by_name: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
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
    raw_failed = payload.get("failed_reviews") or []
    if not isinstance(raw_failed, list):
        raise ValidationError("failed_reviews must be a list")
    revs_by_vec: dict[str, list[dict[str, Any]]] = {v["name"]: [] for v in vectors}
    failed_by_vec: dict[str, list[dict[str, Any]]] = {v["name"]: [] for v in vectors}
    for idx, rr in enumerate(raw_revs):
        _parse_one_review_entry(rr, idx, revs_by_vec, failed_by_vec, pool_by_key)
    for idx, fr in enumerate(raw_failed):
        _parse_failed_entry(fr, f"failed_reviews[{idx}]", failed_by_vec, pool_by_key)
    return vectors, revs_by_vec, failed_by_vec


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
        eff[vn] = w_h * sh + w_g * sg + w_u * su
        gap_driven[vn] = eff[vn] > sh + _SQRT_EPS
    return eff, gap_driven


def _vector_meets_target(vs: dict[str, Any], m_cur: float, target_val: float | None) -> bool:
    if target_val is None:
        return False
    scaled = {c: m * m_cur for c, m in vs["spec"]["commit_masses"].items()}
    return compose_vector_risk(scaled, vs["spec"]["phi"]) <= target_val + _SQRT_EPS


def _best_vector_marginal(
    risky_open: list[dict[str, Any]],
    eff_shares: dict[str, float],
    counts: dict[str, int],
    cap_by_vec: dict[str, int],
    catch_table: dict[str, Any],
    unit_cost: float,
    target_val: float | None,
) -> str | None:
    best_key: tuple[float, int] | None = None
    best_name: str | None = None
    for vs in risky_open:
        vn = vs["spec"]["name"]
        if counts[vn] >= cap_by_vec[vn]:
            continue
        _, m_cur, _, _ = catch_miss_at(catch_table, counts[vn])
        if _vector_meets_target(vs, m_cur, target_val):
            continue
        _, m_nxt, _, _ = catch_miss_at(catch_table, counts[vn] + 1)
        gain = (eff_shares[vn] * max(0.0, m_cur - m_nxt)) / unit_cost
        cand = (gain, -counts[vn])
        if gain > _SQRT_EPS and (best_key is None or cand[0] > best_key[0] + _SQRT_EPS * max(1.0, best_key[0]) or (abs(cand[0] - best_key[0]) <= _SQRT_EPS * max(1.0, best_key[0]) and cand[1] > best_key[1])):
            best_key, best_name = cand, vn
    return best_name


def _risk_scaled_wave_slots(eff_shares: dict[str, float], pool_len: int) -> tuple[int, float]:
    """Level-invariant risk-proportional Wave-1 demand: ceil(P * sum_V (s_eff(V) / max(s_eff)))."""
    if not eff_shares or pool_len <= 0:
        return 0, 0.0
    peak = max(eff_shares.values())
    if peak <= 0.0:
        return len(eff_shares), float(len(eff_shares))
    c_risk = sum(s / peak for s in eff_shares.values())
    demand = max(len(eff_shares), min(len(eff_shares) * pool_len, int(math.ceil(pool_len * c_risk - _SQRT_EPS))))
    return demand, c_risk


def _wave_stop_reason(
    risky_open: list[dict[str, Any]],
    budget_exceeded: bool,
    all_saturated: bool,
    capped_by_risk_demand: bool,
    explicit_wave_cap: bool,
    slots_left: int,
    unused_budget: float | None,
) -> str:
    if not risky_open:
        return "no_open_risky_vectors"
    if budget_exceeded:
        return "budget_exceeded_by_minimum_coverage"
    if all_saturated:
        return "pool_saturated"
    if capped_by_risk_demand:
        return "risk_scaled_wave_capacity"
    if slots_left == 0:
        return "wave_budget_reached" if (explicit_wave_cap and (unused_budget is None or unused_budget > _SQRT_EPS)) else "budget_exhausted"
    return "pool_saturated"


def _compute_wave_slot_budget(
    cfg: dict[str, Any],
    max_slots: int,
    risk_demand: int,
    unit_cost: float,
) -> tuple[int, bool, bool]:
    """Take min(budget_slots, wave_cap, risk_demand) so explicit wave caps never override risk scaling."""
    budget_slots = max_slots
    if cfg["budget_minutes"] is not None:
        rem = max(0.0, cfg["budget_minutes"] - cfg["elapsed_minutes"])
        budget_slots = min(max_slots, int((rem + _SQRT_EPS * max(1.0, unit_cost)) // unit_cost))
    explicit_cap = False
    wave_cap = max_slots
    if cfg["wave_budget_minutes"] is not None:
        explicit_cap = True
        wave_cap = min(wave_cap, int((cfg["wave_budget_minutes"] + _SQRT_EPS * max(1.0, unit_cost)) // unit_cost))
    if cfg["max_wave_reviewers"] is not None:
        explicit_cap = True
        wave_cap = min(wave_cap, int(cfg["max_wave_reviewers"]))
    if cfg["target_val"] is not None:
        return min(budget_slots, wave_cap), explicit_cap, False
    ceiling = min(budget_slots, wave_cap)
    capped_by_risk = risk_demand < ceiling and risk_demand < max_slots
    return min(ceiling, risk_demand), explicit_cap, capped_by_risk


def _inline_wave_outcome(risky_all: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build inline outcome from reviewer- or lead/seam-proven blockers so gap weights adapt immediately."""
    if not any(vs["all_bugs"] or vs["seam_failed"] for vs in risky_all):
        return []
    tot_h = sum(vs["spec"]["alloc_weight"] for vs in risky_all)
    tot_g = sum(vs["spec"]["gap_mass"] for vs in risky_all)
    n_all = float(max(1, len(risky_all)))
    return [{
        "review_id": "inline_current_wave",
        "vectors": [
            {
                "name": vs["spec"]["name"],
                "hist_share": (vs["spec"]["alloc_weight"] / tot_h) if tot_h > 0.0 else (1.0 / n_all),
                "gap_share": (vs["spec"]["gap_mass"] / tot_g) if tot_g > 0.0 else (1.0 / n_all),
                "reviewers_completed": max(len(vs["distinct_runs"]), 1 if vs["has_external_proof"] else 0),
                "observed_blockers": max(len(vs["all_bugs"]), 1 if vs["seam_failed"] else 0),
            }
            for vs in risky_all
        ],
    }]


def _compute_budget_recharge(
    vec_outputs: list[dict[str, Any]],
    cfg: dict[str, Any],
    rem_budget: float | None,
    unit_cost: float,
) -> dict[str, Any]:
    """Evidence-driven capacity recharge for verified blockers or failed/blocked model transfers."""
    if rem_budget is None:
        return {"recharged_slots": 0, "recharged_minutes": 0.0, "effective_budget_minutes": None, "effective_remaining_budget": None, "recharge_reason": "none", "recharge_capped_by_max_budget": False}
    blocker_driven = [
        vo for vo in vec_outputs
        if (vo["observed_blockers"] > 0 or vo["seam_failed"]) and vo["action"] == "continue"
    ]
    transfer_driven = [
        vo for vo in vec_outputs
        if vo["reason"] in ("gap_brief_transfer_after_model_failure", "transfer_after_model_failure") and vo["action"] == "continue"
    ]
    eligible_names = {vo["name"] for vo in blocker_driven} | {vo["name"] for vo in transfer_driven}
    eligible_models = [
        m for vo in vec_outputs
        if vo["name"] in eligible_names
        for m in vo["next_models"]
    ]
    needed_cost = sum(float(m.get("cost_minutes") or unit_cost) for m in eligible_models)
    shortfall = max(0.0, needed_cost - rem_budget)
    if shortfall <= _SQRT_EPS:
        return {
            "recharged_slots": 0, "recharged_minutes": 0.0,
            "effective_budget_minutes": round(cfg["budget_minutes"], 6),
            "effective_remaining_budget": round(rem_budget, 6),
            "recharge_reason": "none", "recharge_capped_by_max_budget": False,
        }
    max_extra = shortfall
    capped = False
    if cfg["max_budget_minutes"] is not None:
        headroom = max(0.0, cfg["max_budget_minutes"] - cfg["budget_minutes"])
        capped = shortfall > headroom + _SQRT_EPS
        max_extra = min(shortfall, headroom)
    eff_total = cfg["budget_minutes"] + max_extra
    eff_rem = rem_budget + max_extra
    recharged_slots = int((max_extra + _SQRT_EPS * max(1.0, unit_cost)) // unit_cost) if max_extra > _SQRT_EPS else 0
    active_reason = "active_blockers_unsaturated" if blocker_driven else "model_failure_transfer"
    reason = "capped_by_max_budget" if (capped and recharged_slots == 0) else active_reason
    return {
        "recharged_slots": recharged_slots,
        "recharged_minutes": round(max_extra, 6),
        "effective_budget_minutes": round(eff_total, 6),
        "effective_remaining_budget": round(eff_rem, 6),
        "recharge_reason": reason,
        "recharge_capped_by_max_budget": capped,
    }


def _enforce_hard_max_budget(
    vec_outputs: list[dict[str, Any]],
    eff_rem: float,
    unit_cost: float,
) -> tuple[int, list[dict[str, str]]]:
    """Enforce hard max_budget_minutes strictly by trimming lower-priority next_models to fit eff_rem."""
    candidates = [
        (
            (
                m_idx,
                0 if (vo["observed_blockers"] > 0 and not (vo["estimate"] or {}).get("informative", True)) else 1,
                -float((vo["estimate"] or {}).get("estimated_unfound") or 0.0),
                -vo["observed_blockers"],
                -vo["share"],
                vo["name"],
            ),
            v_idx,
            m_dict,
        )
        for v_idx, vo in enumerate(vec_outputs)
        if vo["action"] == "continue"
        for m_idx, m_dict in enumerate(vo["next_models"])
    ]
    candidates.sort(key=lambda item: item[0])
    kept: dict[int, list[dict[str, Any]]] = {i: [] for i in range(len(vec_outputs))}
    spent = 0.0
    for _, v_idx, m_dict in candidates:
        m_cost = float(m_dict.get("cost_minutes") or unit_cost)
        if spent + m_cost <= eff_rem + _SQRT_EPS * max(1.0, eff_rem):
            kept[v_idx].append(m_dict)
            spent += m_cost

    trimmed_total = 0
    notes: list[dict[str, str]] = []
    for v_idx, vo in enumerate(vec_outputs):
        if vo["action"] != "continue":
            continue
        dropped = len(vo["next_models"]) - len(kept[v_idx])
        if dropped <= 0:
            continue
        trimmed_total += dropped
        vo["next_models"] = kept[v_idx]
        notes.append({"vector": vo["name"], "reason": f"max_budget_minutes hard cap trimmed {dropped} reviewer(s)"})
        if not vo["next_models"]:
            vo["action"] = "flag"
            vo["verdict"] = "budget_exhausted"
            vo["reason"] = "max_budget_reached"
            vo["landing_blocked"] = True
    return trimmed_total, notes


def _is_vector_open_for_wave(vs: dict[str, Any], cfg: dict[str, Any], catch_rates: dict[tuple[str, str], CatchRate]) -> bool:
    """Return True if a positive-risk non-seam vector still needs reviewer allocation in this wave."""
    if vs["spec"]["risk"] <= 0.0 or vs["seam_backed"]:
        return False
    k, d_cnt = len(vs["distinct_runs"]), len(vs["all_bugs"])
    if k < 2 or d_cnt > 0 or vs["seam_failed"] or vs["failed_gap"] or cfg["target_val"] is not None:
        return True
    if cfg["unreachable"] and vs["explicit_standard_only"] and not vs["prior_gap"]:
        return True
    cal = _joint_per_bug_calibration([r["model"].key for r in vs["distinct_runs"]], catch_rates)
    return bool(cal is not None and not cal["can_stop"])


def _allocate_wave_extra(
    vec_state: list[dict[str, Any]],
    cfg: dict[str, Any],
    outcomes: list[dict[str, Any]],
    catch_rates: dict[tuple[str, str], CatchRate],
) -> tuple[dict[str, int], dict[str, bool], dict[str, Any], dict[str, Any]]:
    """Pure greedy, level-invariant Wave-1 allocation scaled by risk concentration (never capped at 2)."""
    reachable_pool, catch_table = cfg["reachable_pool"], cfg["catch_table"]
    counts = {vs["spec"]["name"]: len(vs["distinct_runs"]) for vs in vec_state}
    extra = {vs["spec"]["name"]: 0 for vs in vec_state}
    gap_driven = {vs["spec"]["name"]: False for vs in vec_state}
    risky_all = [vs for vs in vec_state if vs["spec"]["risk"] > 0.0 and not vs["seam_backed"]]
    risky_open = [vs for vs in risky_all if _is_vector_open_for_wave(vs, cfg, catch_rates)]
    has_gap = any(vs["spec"]["gap_mass"] > 0.0 for vs in risky_all)
    experts: tuple[str, ...] = ("hist", "gap", "unif") if has_gap else ("hist", "unif")
    all_outcomes = [*outcomes, *_inline_wave_outcome(risky_all)]
    expert_info = _fit_expert_weights(all_outcomes, experts, catch_table)
    if risky_all:
        _, all_gap_driven = _effective_vector_shares(risky_all, expert_info["_raw_weights"])
        gap_driven.update(all_gap_driven)
    meta: dict[str, Any] = {
        "risky_open": risky_open, "explicit_wave_cap": False, "all_saturated": False,
        "capped_by_risk_demand": False, "risk_scaled_wave_slots": 0, "risk_concentration": 0.0, "slots_left": 0,
    }
    if not risky_open or not reachable_pool:
        return extra, gap_driven, expert_info, meta

    eff_shares, _ = _effective_vector_shares(risky_open, expert_info["_raw_weights"])
    avail_by_vec = {
        vs["spec"]["name"]: sum(1 for m in reachable_pool if m.key not in vs["excluded_keys"])
        for vs in vec_state
    }
    cap_by_vec = {vn: counts[vn] + avail_by_vec[vn] for vn in counts}
    max_slots = sum(avail_by_vec[vs["spec"]["name"]] for vs in risky_open)
    unit_cost = statistics.fmean([m.cost_minutes for m in reachable_pool if m.cost_minutes is not None] or [1.0])
    risk_demand, c_risk = _risk_scaled_wave_slots(eff_shares, len(reachable_pool))
    slot_budget, explicit_cap, capped_by_risk = _compute_wave_slot_budget(
        cfg, max_slots, risk_demand, unit_cost,
    )
    meta["explicit_wave_cap"] = explicit_cap
    meta["capped_by_risk_demand"] = capped_by_risk
    meta["risk_scaled_wave_slots"] = risk_demand
    meta["risk_concentration"] = round(c_risk, 6)

    unreviewed = [
        vs["spec"]["name"] for vs in risky_open
        if counts[vs["spec"]["name"]] == 0 and avail_by_vec[vs["spec"]["name"]] > 0
    ]
    for vn in unreviewed:
        counts[vn] += 1
        extra[vn] += 1
    slots_left = max(0, slot_budget - len(unreviewed))

    while slots_left > 0:
        best_name = _best_vector_marginal(risky_open, eff_shares, counts, cap_by_vec, catch_table, unit_cost, cfg["target_val"])
        if best_name is None:
            break
        counts[best_name] += 1
        extra[best_name] += 1
        slots_left -= 1
    meta["slots_left"] = slots_left
    meta["all_saturated"] = all(counts[vs["spec"]["name"]] >= cap_by_vec[vs["spec"]["name"]] for vs in risky_open)
    return extra, gap_driven, expert_info, meta


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


def _secondary_expansion_count(est: dict[str, Any], zero_singletons: bool, unused_count: int) -> int:
    """Scale Wave 2+ parallel expansion on D > 0 vectors directly from capture-recapture evidence."""
    if unused_count <= 1 or zero_singletons:
        return min(1, unused_count)
    if not est.get("informative"):
        return unused_count
    if est.get("confidence_alpha") is not None and est.get("estimated_unfound_upper") is None:
        return unused_count
    est_u = float(est.get("estimated_unfound") or 0.0)
    return min(unused_count, max(1, int(math.ceil(est_u))))


def _decide_positive_bugs(
    vs: dict[str, Any],
    cfg: dict[str, Any],
    planned_extra: int,
) -> tuple[str, str, str, bool, dict[str, Any] | None, list[ModelSpec]]:
    runs = vs["distinct_runs"]
    unused = [m for m in cfg["reachable_pool"] if m.key not in vs["excluded_keys"]]
    has_blocked = bool(cfg["unreachable"] or vs["failed_keys"])
    if len(runs) < 2:
        if unused:
            return "continue", "continue", "second_independent_model_required", True, None, _pick_models(cfg["reachable_pool"], vs["excluded_keys"], vs["used_providers"], cfg["worker_key"], max(1, planned_extra))
        if has_blocked:
            return "flag", "pool_exhausted", "remaining_pool_models_unreachable", True, None, []
        return "stop", "fix_and_rereview", "single_model_pool_fix_and_rereview", True, None, []

    est, zero_singletons = _capture_recapture_summary(runs, cfg["confidence_alpha"])
    if est["can_stop"]:
        return "stop", "fix_and_rereview", "saturated_observable_class", True, est, []
    if unused:
        reason = "unanimous_small_count_needs_capture_recapture_check" if zero_singletons else "models_still_finding_new_bugs"
        expand_n = _secondary_expansion_count(est, zero_singletons, len(unused))
        return "continue", "continue", reason, True, est, _pick_models(cfg["reachable_pool"], vs["excluded_keys"], vs["used_providers"], cfg["worker_key"], expand_n)
    if has_blocked:
        return "flag", "pool_exhausted", "remaining_pool_models_unreachable", True, est, []
    if zero_singletons:
        return "stop", "fix_and_rereview", "all_models_unanimous_fix_and_rereview", True, est, []
    return "flag", "pool_exhausted", "pool_exhausted_with_open_singletons", True, est, []


def _needs_gap_transfer(vs: dict[str, Any], cfg: dict[str, Any], gap_lifted: bool) -> bool:
    if vs["prior_gap"]:
        return False
    if vs["failed_gap"]:
        return True
    return bool(gap_lifted and (cfg["unreachable"] or vs["failed_keys"]) and vs["explicit_standard_only"])


def _decide_zero_bugs(
    vs: dict[str, Any],
    cfg: dict[str, Any],
    rb: dict[str, Any],
    catch_rates: dict[tuple[str, str], CatchRate],
    planned_extra: int,
    needs_gap_transfer: bool,
) -> tuple[str, str, str, bool, dict[str, Any] | None, list[ModelSpec]]:
    runs = vs["distinct_runs"]
    k = len(runs)
    unused = [m for m in cfg["reachable_pool"] if m.key not in vs["excluded_keys"]]
    has_blocked = bool(cfg["unreachable"] or vs["failed_keys"])
    budget_done = cfg["budget_minutes"] is not None and (cfg["elapsed_minutes"] >= cfg["budget_minutes"])

    cal_est = _joint_per_bug_calibration([r["model"].key for r in runs], catch_rates)
    if cal_est is not None and cfg["target_val"] is not None:
        cal_est["can_stop"] = (not cal_est["jointly_missed_bugs"]) and (cal_est["jeffreys_joint_miss_prob"] <= cfg["target_val"])

    if needs_gap_transfer and not unused:
        return "flag", "pool_exhausted", "gap_brief_unrun_pool_exhausted", True, cal_est, []
    if k == 0:
        if unused and (not budget_done or vs["failed_runs"]):
            want = min(len(unused), max(1, len(vs["failed_runs"]))) if (budget_done and vs["failed_runs"]) else max(1, planned_extra)
            reason = "transfer_after_model_failure" if vs["failed_runs"] else "initial_mass_allocation"
            return "continue", "continue", reason, False, None, _pick_models(cfg["reachable_pool"], vs["excluded_keys"], vs["used_providers"], cfg["worker_key"], want)
        return "flag", ("pool_exhausted" if not unused else "budget_exhausted"), "no_review_completed", True, None, []
    if cal_est is not None:
        if cal_est["can_stop"] and k >= 2 and not needs_gap_transfer:
            return "stop", "clean_stop", "calibrated_zero_shared_blind_spots", False, cal_est, []
        if unused and (not budget_done or needs_gap_transfer or vs["failed_runs"]):
            reason = "gap_brief_transfer_after_model_failure" if needs_gap_transfer else ("shared_blind_spot_detected" if cal_est["jointly_missed_bugs"] else "calibration_target_unmet")
            return "continue", "continue", reason, False, cal_est, _pick_models(cfg["reachable_pool"], vs["excluded_keys"], vs["used_providers"], cfg["worker_key"], 1)
        reason = "gap_brief_unrun_pool_exhausted" if needs_gap_transfer else ("shared_blind_spot_unclosed" if cal_est["jointly_missed_bugs"] else "remaining_pool_models_unreachable")
        return "flag", "pool_exhausted", reason, True, cal_est, []
    if needs_gap_transfer and k >= 2:
        return "continue", "continue", "gap_brief_transfer_after_model_failure", False, None, _pick_models(cfg["reachable_pool"], vs["excluded_keys"], vs["used_providers"], cfg["worker_key"], 1)
    if k < 2 and not unused and has_blocked:
        return "flag", "pool_exhausted", "remaining_pool_models_unreachable", True, None, []
    if budget_done:
        if k < 2 and vs["failed_runs"] and unused:
            return "continue", "continue", "transfer_after_model_failure", False, None, _pick_models(cfg["reachable_pool"], vs["excluded_keys"], vs["used_providers"], cfg["worker_key"], 1)
        return ("flag" if k < 2 else "stop"), "budget_exhausted", "budget_exhausted", (k < 2), None, []
    if k < 2 and unused:
        reason = "transfer_after_model_failure" if vs["failed_runs"] else "second_independent_model_required"
        return "continue", "continue", reason, False, None, _pick_models(cfg["reachable_pool"], vs["excluded_keys"], vs["used_providers"], cfg["worker_key"], 1)
    if cfg["target_val"] is not None and rb["residual_risk"] is not None and rb["residual_risk"] <= cfg["target_val"]:
        return "stop", "clean_stop", "residual_below_target", False, None, []
    if cfg["target_val"] is not None and unused:
        return "continue", "continue", "target_not_yet_met", False, None, _pick_models(cfg["reachable_pool"], vs["excluded_keys"], vs["used_providers"], cfg["worker_key"], 1)
    return "stop", "clean_stop", "independent_models_clean", False, None, []


def _dedupe_active_failures(failed_runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate repeat failure entries for the same model on one vector, preserving gap_brief metadata."""
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for f in failed_runs:
        key = f["model"].key
        prev = by_key.get(key)
        bm = f["brief_mode"] or (prev["brief_mode"] if prev else "")
        if prev and prev["brief_mode"] in ("gap_brief", "standard_with_gap_focus") and bm not in ("gap_brief", "standard_with_gap_focus"):
            bm = prev["brief_mode"]
        by_key[key] = {**f, "brief_mode": bm}
    return list(by_key.values())


def _build_vector_state(
    v: dict[str, Any],
    runs: list[dict[str, Any]],
    failed_runs: list[dict[str, Any]],
    seams_by_name: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    seen_keys: set[tuple[str, str]] = set()
    distinct_runs: list[dict[str, Any]] = []
    violations: list[str] = []
    for r in runs:
        if r["model"].key in seen_keys:
            violations.append(f"duplicate_model_on_vector:{r['model'].label}")
            continue
        seen_keys.add(r["model"].key)
        distinct_runs.append(r)
    active_failures = _dedupe_active_failures(failed_runs)
    failed_keys = {f["model"].key for f in active_failures}
    reviewer_bugs = sorted({b for r in distinct_runs for b in r["verified"]})
    known_blockers = list(v.get("known_blockers") or [])
    seam_failed = bool(v["seams"]) and any(seams_by_name[s]["verdict"] != "verified" for s in v["seams"])
    prior_gap = any(r.get("brief_mode") in ("gap_brief", "standard_with_gap_focus") for r in distinct_runs)
    failed_gap = any(f.get("brief_mode") in ("gap_brief", "standard_with_gap_focus") for f in active_failures)
    explicit_standard_only = bool(distinct_runs) and all(r.get("brief_mode") == "standard" for r in distinct_runs)
    return {
        "spec": v,
        "distinct_runs": distinct_runs,
        "seen_keys": seen_keys,
        "failed_runs": active_failures,
        "failed_keys": failed_keys,
        "excluded_keys": seen_keys | failed_keys,
        "used_providers": {r["model"].provider for r in distinct_runs},
        "reviewer_bugs": reviewer_bugs,
        "known_blockers": known_blockers,
        "all_bugs": sorted(set(reviewer_bugs) | set(known_blockers)),
        "violations": violations,
        "seam_backed": bool(v["seams"]) and (not seam_failed),
        "seam_failed": seam_failed,
        "has_external_proof": bool(known_blockers) or seam_failed,
        "prior_gap": prior_gap,
        "failed_gap": failed_gap,
        "explicit_standard_only": explicit_standard_only,
    }


def _decide_external_blockers(
    vs: dict[str, Any],
    cfg: dict[str, Any],
    planned_extra: int,
) -> tuple[str, str, str, bool, dict[str, Any] | None, list[ModelSpec]]:
    unused = [m for m in cfg["reachable_pool"] if m.key not in vs["excluded_keys"]]
    k = len(vs["distinct_runs"])
    if unused:
        want = max(1, planned_extra) if k == 0 else min(len(unused), max(1, len(vs["known_blockers"])))
        return "continue", "continue", "known_blockers_need_deeper_review", True, None, _pick_models(cfg["reachable_pool"], vs["excluded_keys"], vs["used_providers"], cfg["worker_key"], want)
    if cfg["unreachable"] or vs["failed_keys"]:
        return "flag", "pool_exhausted", "remaining_pool_models_unreachable", True, None, []
    return "stop", "fix_and_rereview", "known_blockers_fix_and_rereview", True, None, []


def _decide_vector_outcome(
    vs: dict[str, Any],
    cfg: dict[str, Any],
    rb: dict[str, Any],
    catch_rates: dict[tuple[str, str], CatchRate],
    planned_extra: int,
    gap_lifted: bool,
    violations: list[str],
) -> tuple[str, str, str, bool, dict[str, Any] | None, list[ModelSpec]]:
    v, runs = vs["spec"], vs["distinct_runs"]
    k, d_rev = len(runs), len(vs["reviewer_bugs"])
    non_worker_runs = [r for r in runs if cfg["worker_key"] is None or r["model"].key != cfg["worker_key"]]
    non_worker_avail = [m for m in cfg["reachable_pool"] if m.key not in vs["excluded_keys"] and (cfg["worker_key"] is None or m.key != cfg["worker_key"])]

    if k > 0 and not non_worker_runs and non_worker_avail:
        violations.append("worker_model_only")
        return "continue", "continue", "non_worker_model_required", False, None, _pick_models(cfg["reachable_pool"], vs["excluded_keys"], vs["used_providers"], cfg["worker_key"], 1)
    if (v["risk"] == 0.0 or vs["seam_backed"]) and d_rev == 0 and (not vs["has_external_proof"]) and k >= 1:
        reason = "seam_verified_single_clean" if vs["seam_backed"] else "zero_risk_single_clean"
        return "stop", "clean_stop", reason, False, None, []
    if (v["risk"] == 0.0 or vs["seam_backed"]) and d_rev == 0 and (not vs["has_external_proof"]):
        unused = [m for m in cfg["reachable_pool"] if m.key not in vs["excluded_keys"]]
        if not unused:
            return "flag", "pool_exhausted", "remaining_pool_models_unreachable", True, None, []
        return "continue", "continue", "needs_initial_review", False, None, _pick_models(cfg["reachable_pool"], vs["excluded_keys"], vs["used_providers"], cfg["worker_key"], 1)
    if d_rev > 0:
        return _decide_positive_bugs(vs, cfg, planned_extra)
    if vs["has_external_proof"]:
        return _decide_external_blockers(vs, cfg, planned_extra)
    return _decide_zero_bugs(vs, cfg, rb, catch_rates, planned_extra, _needs_gap_transfer(vs, cfg, gap_lifted))


def _evaluate_one_vector(
    vs: dict[str, Any],
    cfg: dict[str, Any],
    catch_rates: dict[tuple[str, str], CatchRate],
    planned_extra: int,
    gap_lifted: bool,
    total_mass: float,
    total_gap: float,
) -> dict[str, Any]:
    v, runs = vs["spec"], vs["distinct_runs"]
    k, D = len(runs), len(vs["all_bugs"])
    violations = list(vs["violations"])
    rb = residual_risk_with_bracket(v["commit_masses"], v["phi"], k, cfg["catch_table"])
    action, verdict, reason, blocked, est, next_models = _decide_vector_outcome(vs, cfg, rb, catch_rates, planned_extra, gap_lifted, violations)

    share = round(v["mass"] / total_mass, 6) if total_mass > 0.0 else 0.0
    gap_share = round(v["gap_mass"] / total_gap, 6) if total_gap > 0.0 else 0.0
    return {
        "name": v["name"], "risk": round_risk(v["risk"]), "mass": round(v["mass"], 6), "share": share,
        "gap_mass": round(v["gap_mass"], 6), "gap_share": gap_share, "gap_lifted": gap_lifted, "brief_mode": "standard",
        "phi": round(v["phi"], 6), "target": v["target"], "finder_checks": v["finder_checks"],
        "kind_scope_upper_bound": v["kind_scope_upper_bound"], **rb,
        "reviewers_completed": k, "failed_reviews": len(vs["failed_runs"]),
        "observed_blockers": D, "known_blockers": len(vs["known_blockers"]),
        "seam_failed": vs["seam_failed"], "action": action, "verdict": verdict,
        "reason": reason, "landing_blocked": blocked, "rule_violations": violations,
        "estimate": est, "plain_range": format_plain_range(est),
        "next_models": [m.to_dict() for m in next_models],
    }


def _model_brief_modes(
    models: list[dict[str, Any]],
    gap_lifted: bool,
    k: int,
    prior_gap: bool,
    worker_key: tuple[str, str] | None,
    gap_slot_idx: int,
    force_gap: bool,
) -> list[str]:
    n = len(models)
    if n <= 0 or prior_gap or (not gap_lifted and not force_gap):
        return ["standard"] * n
    if k == 0 and n == 1:
        return ["standard_with_gap_focus"]
    non_worker = [i for i, m in enumerate(models) if (m["provider"], m["model"]) != worker_key]
    candidates = non_worker or list(range(n))
    chosen = candidates[gap_slot_idx % len(candidates)]
    return ["gap_brief" if i == chosen else "standard" for i in range(n)]


def _vector_brief_summary(modes: list[str]) -> str:
    unique = set(modes)
    if unique == {"standard_with_gap_focus"}:
        return "standard_with_gap_focus"
    if unique == {"gap_brief"}:
        return "gap_brief"
    if "gap_brief" in unique:
        return "standard_plus_gap_brief"
    return "standard"


def _assign_reviewer_brief_modes(
    vec_outputs: list[dict[str, Any]],
    vec_state_by_name: dict[str, dict[str, Any]],
    worker_key: tuple[str, str] | None,
) -> None:
    """Assign brief_mode per reviewer: rotate gap_brief across non-worker models and keep 1-reviewer vectors standard+gap."""
    gap_slot_idx = 0
    for vo in vec_outputs:
        vs = vec_state_by_name[vo["name"]]
        force_gap = bool(vs["failed_gap"] or vo["reason"] == "gap_brief_transfer_after_model_failure")
        modes = _model_brief_modes(
            vo["next_models"],
            vo["gap_lifted"],
            vo["reviewers_completed"],
            vs["prior_gap"],
            worker_key,
            gap_slot_idx,
            force_gap,
        )
        if "gap_brief" in modes and len(modes) >= 2:
            gap_slot_idx += 1
        vo["next_models"] = [{**m, "brief_mode": bm} for m, bm in zip(vo["next_models"], modes)]
        vo["brief_mode"] = _vector_brief_summary(modes)


def _format_next_action(vo: dict[str, Any]) -> str:
    has_non_std = any(m.get("brief_mode", "standard") != "standard" for m in vo["next_models"])
    models_s = ", ".join(
        f"{m['provider']}/{m['model']} [{m['brief_mode']}]" if has_non_std else f"{m['provider']}/{m['model']}"
        for m in vo["next_models"]
    )
    return f"{vo['name']}: dispatch {models_s} ({vo['reason']})"


def _collect_payload_receipts(payload: dict[str, Any], external_receipts: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = list(external_receipts or [])
    raw_inline = payload.get("dispatch_receipts")
    if raw_inline is not None:
        if not isinstance(raw_inline, list):
            raise ValidationError("dispatch_receipts must be a list")
        receipts.extend(r for r in raw_inline if isinstance(r, dict))
    raw_dir = payload.get("receipts_dir")
    if isinstance(raw_dir, str) and raw_dir.strip():
        receipts.extend(load_dispatch_receipts([raw_dir.strip()]))
    elif isinstance(raw_dir, list):
        receipts.extend(load_dispatch_receipts([str(p) for p in raw_dir if str(p).strip()]))
    return receipts


def evaluate_ledger(
    payload: dict[str, Any],
    *,
    external_catch_rates: dict[tuple[str, str], CatchRate] | None = None,
    external_outcomes: list[dict[str, Any]] | None = None,
    external_receipts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Evaluate structural gates, capture-recapture saturation, and dynamic gap-hedged reviewer allocation."""
    if not isinstance(payload, dict):
        raise ValidationError("ledger input must be a JSON object")
    cfg = _parse_config(payload)
    catch_rates = {**(external_catch_rates or {}), **parse_catch_rate_map(payload.get("model_catch_rates"), "model_catch_rates")}
    seams_by_name, seam_outputs, any_seam_failed = _parse_seams(payload.get("seams"))
    vectors, revs_by_vec, failed_by_vec = _parse_vectors_and_reviews(payload, cfg["pool_by_key"], seams_by_name)
    _validate_no_contradictory_reviews(revs_by_vec, failed_by_vec)
    all_receipts = _collect_payload_receipts(payload, external_receipts)
    if all_receipts:
        _merge_receipt_failures(all_receipts, revs_by_vec, failed_by_vec, cfg["pool_by_key"])
    _promote_blocked_models(cfg, failed_by_vec)
    raw_outcomes = payload.get("past_review_outcomes") or []
    if not isinstance(raw_outcomes, list):
        raise ValidationError("past_review_outcomes must be a list")
    outcomes = [*(external_outcomes or []), *raw_outcomes]

    vec_state = [_build_vector_state(v, revs_by_vec[v["name"]], failed_by_vec[v["name"]], seams_by_name) for v in vectors]
    vec_state_by_name = {vs["spec"]["name"]: vs for vs in vec_state}
    planned_extra, gap_driven, expert_info, wave_meta = _allocate_wave_extra(vec_state, cfg, outcomes, catch_rates)
    phi_global = vectors[0]["phi"] if vectors else 0.0
    total_mass = sum(v["mass"] for v in vectors)
    total_gap = sum(v["gap_mass"] for v in vectors)
    change_risk = compose_change_risk([v["commit_masses"] for v in vectors], phi_global)

    vec_outputs = [
        _evaluate_one_vector(vs, cfg, catch_rates, planned_extra[vs["spec"]["name"]], gap_driven[vs["spec"]["name"]], total_mass, total_gap)
        for vs in vec_state
    ]
    unit_cost = statistics.fmean([m.cost_minutes for m in cfg["reachable_pool"] if m.cost_minutes is not None] or [1.0])
    rem_budget = None if cfg["budget_minutes"] is None else round(max(0.0, cfg["budget_minutes"] - cfg["elapsed_minutes"]), 6)
    recharge = _compute_budget_recharge(vec_outputs, cfg, rem_budget, unit_cost)
    hard_cap_rem = None if cfg["max_budget_minutes"] is None else round(max(0.0, cfg["max_budget_minutes"] - cfg["elapsed_minutes"]), 6)
    eff_rem = recharge["effective_remaining_budget"]
    if eff_rem is not None and hard_cap_rem is not None and hard_cap_rem < eff_rem:
        eff_rem = hard_cap_rem
        recharge["effective_remaining_budget"] = hard_cap_rem
        recharge["effective_budget_minutes"] = round(min(recharge["effective_budget_minutes"], cfg["max_budget_minutes"]), 6)
        re_extra = max(0.0, recharge["effective_budget_minutes"] - cfg["budget_minutes"])
        recharge["recharged_minutes"] = round(re_extra, 6)
        recharge["recharged_slots"] = int((re_extra + _SQRT_EPS * max(1.0, unit_cost)) // unit_cost) if re_extra > _SQRT_EPS else 0
        recharge["recharge_capped_by_max_budget"] = True
        if recharge["recharged_slots"] == 0 and recharge["recharge_reason"] != "none":
            recharge["recharge_reason"] = "capped_by_max_budget"
    enforce_rem = hard_cap_rem if eff_rem is None else (min(eff_rem, hard_cap_rem) if hard_cap_rem is not None else None)
    trimmed_slots, trim_notes = (
        _enforce_hard_max_budget(vec_outputs, enforce_rem, unit_cost)
        if enforce_rem is not None
        else (0, [])
    )
    if trimmed_slots > 0 and recharge["recharged_slots"] == 0 and recharge["recharge_reason"] != "none":
        recharge["recharge_reason"] = "capped_by_max_budget"
        recharge["recharge_capped_by_max_budget"] = True
    _assign_reviewer_brief_modes(vec_outputs, vec_state_by_name, cfg["worker_key"])

    allocated_by_vec = {vo["name"]: vo["next_models"] for vo in vec_outputs}
    next_actions = [_format_next_action(vo) for vo in vec_outputs if vo["action"] == "continue"]
    lanes_lines = [
        f"ledger: {vo['name']} risk={vo['risk']:.4f} share={vo['share']:.4f} k={vo['reviewers_completed']} D={vo['observed_blockers']} action={vo['action']} reason={vo['reason']}"
        for vo in vec_outputs
    ]
    any_flag = any(vo["action"] == "flag" for vo in vec_outputs)
    any_continue = any(vo["action"] == "continue" for vo in vec_outputs)
    any_blocked = any_seam_failed or any(vo["landing_blocked"] for vo in vec_outputs)

    ch_rb = change_residual_risk_with_bracket([(vs["spec"]["commit_masses"], len(vs["distinct_runs"])) for vs in vec_state], phi_global, cfg["catch_table"])
    overall = "flagged" if (any_flag or any_seam_failed) else ("continue" if any_continue else "complete")
    planned_models = [m for ms in allocated_by_vec.values() for m in ms]
    planned_cost = round(sum(float(m.get("cost_minutes") or unit_cost) for m in planned_models), 6)
    completed_reviewers = sum(vo["reviewers_completed"] for vo in vec_outputs)
    failed_reviewers = sum(vo["failed_reviews"] for vo in vec_outputs)
    returned_slots = sum(vo["reviewers_completed"] for vo in vec_outputs if vo["action"] in ("stop", "flag")) + failed_reviewers
    closed_vectors = sum(1 for vo in vec_outputs if vo["action"] == "stop")
    flagged_vectors = sum(1 for vo in vec_outputs if vo["action"] == "flag")
    open_vectors = sum(1 for vo in vec_outputs if vo["action"] == "continue")
    budget_exceeded = bool(eff_rem is not None and planned_cost > eff_rem + _SQRT_EPS * max(1.0, eff_rem))
    budget_overrun = round(max(0.0, planned_cost - eff_rem), 6) if eff_rem is not None else 0.0
    unused_budget = round(max(0.0, eff_rem - planned_cost), 6) if eff_rem is not None else None
    wave_stop = _wave_stop_reason(
        wave_meta["risky_open"], budget_exceeded, wave_meta["all_saturated"], wave_meta["capped_by_risk_demand"],
        wave_meta["explicit_wave_cap"], wave_meta["slots_left"], unused_budget,
    )
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
    failed_notes = [
        {
            "vector": vs["spec"]["name"],
            "model": f["model"].label,
            "reason": f"{f['status']}: {f['reason']}" + (f" ({f['brief_mode']})" if f["brief_mode"] else ""),
        }
        for vs in vec_state
        for f in vs["failed_runs"]
    ]
    unrun_gap_notes = [
        {"vector": vo["name"], "reason": "gap_brief could not transfer: no remaining reachable approved models in reviewer_pool"}
        for vo in vec_outputs
        if vo["reason"] == "gap_brief_unrun_pool_exhausted"
    ]
    could_not_test = [
        *[{"model": f"{mk[0]}/{mk[1]}", "reason": r} for mk, r in sorted(cfg["unreachable"].items())],
        *failed_notes,
        *unrun_gap_notes,
        *trim_notes,
    ]
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
            "completed_reviewers": completed_reviewers,
            "failed_reviewers": failed_reviewers,
            "returned_slots": returned_slots,
            "failed_slots_returned": failed_reviewers,
            "closed_vectors": closed_vectors,
            "flagged_vectors": flagged_vectors,
            "open_vectors": open_vectors,
            "planned_reviewers": len(planned_models),
            "planned_cost": planned_cost,
            "remaining_budget": rem_budget,
            "unused_budget": unused_budget,
            "wave_budget_minutes": cfg["wave_budget_minutes"],
            "max_wave_reviewers": cfg["max_wave_reviewers"],
            "max_budget_minutes": cfg["max_budget_minutes"],
            "trimmed_by_max_budget_slots": trimmed_slots,
            "risk_scaled_wave_slots": wave_meta["risk_scaled_wave_slots"],
            "risk_concentration": wave_meta["risk_concentration"],
            "budget_exceeded": budget_exceeded,
            "budget_overrun": budget_overrun,
            "wave_stop_reason": wave_stop,
            **recharge,
            "change_risk": ch_risk_rounded,
            **ch_rb,
        },
        "seams": seam_outputs, "vectors": vec_outputs, "next_actions": next_actions,
        "could_not_test": could_not_test,
        "lanes_log_lines": lanes_lines,
    }
