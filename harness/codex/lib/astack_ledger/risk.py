"""Normalized [0, 1) vector risk, additive Bayesian git baseline, and sharp exchangeable catch-table math.

Single source of truth for risk scoring and catch-table bounds:
1. Universal codebase-agnostic git features + blame-based fix tracing authorize shares immediately;
   an agent-built repo-native finder and extra repo features (per-file or per-atom) refine levels.
2. Prequential Additive Bayesian Logistic Regression (exact rank-1 Laplace/ADF + MacKay predictive
   integral, mixed with constant KT baseline via BMA) avoids Cartesian cell-explosion starvation and
   emits exact per-atom `epistemic_var`, `gap_mass`, and `feature_contributions`.
3. Finder diagnostics report raw measured numbers with `level_status: "unverified"` by default.
4. Pinned scorer invariants: power-of-two bucketing for finite numerics, strict pre-base training
   and closed-horizon enforcement, multi-commit file indexing, and commit-grouped whole-change risk.
5. Anchored catch tables report ONLY sharp exchangeable brackets off-anchor (`point: None`).
"""
from __future__ import annotations

import math
import re
import statistics
import subprocess
import sys
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import Any

VALID_RISK_TARGETS = (
    "traced_fix_within_horizon",
    "surfaces_within_window",
    "present_at_review",
)
VALID_CATCH_PROVENANCE = ("prior", "anchored", "measured")
_REVERT_SHA_RE = re.compile(r"This reverts commit ([0-9a-f]{4,64})", re.I)
_BASELINE_FIX_RE = re.compile(r"\b(fix(?:e[sd]|ing)?|bug|hotfix|regression|revert(?:ed|s)?)\b", re.I)
_HUNK_PRE_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+")
_HEX_SHA_RE = re.compile(r"^[0-9a-f]{40,64}$", re.I)

# Derived strictly from IEEE-754 float64 limits (sys.float_info) and Brent (1973) / MacKay (1992):
_EPS = sys.float_info.epsilon
_SQRT_EPS = math.sqrt(_EPS)
_MIN_LOG_FLOAT = math.log(sys.float_info.min)
_MAX_LOG_FLOAT = math.log(sys.float_info.max)
_INV_GOLDEN = (math.sqrt(5.0) - 1.0) / 2.0
_PROBIT_SCALE = math.pi / 8.0


def _clamp_prob(p: float) -> float:
    return max(_EPS, min(1.0 - _EPS, float(p)))


def _sigmoid(z: float) -> float:
    if z >= 0.0:
        return 1.0 / (1.0 + math.exp(-min(z, _MAX_LOG_FLOAT)))
    ez = math.exp(max(z, -_MAX_LOG_FLOAT))
    return ez / (1.0 + ez)


def round_risk(p: float, digits: int = 6) -> float:
    """Round probability strictly into [0.0, 1.0) so display rounding never crosses 1.0."""
    val = round(float(p), digits)
    if val >= 1.0:
        return round(1.0 - 10.0 ** (-digits), digits)
    return max(0.0, val)


def _logsumexp(vals: list[float]) -> float:
    m = max(vals)
    return m if math.isinf(m) else m + math.log(sum(math.exp(v - m) for v in vals))


def _golden_section_max(fn: Callable[[float], float], lo: float, hi: float) -> tuple[float, float]:
    """Converge 1D unimodal maximum to Brent (1973) float64 precision sqrt(eps)."""
    a_l, b_r = float(lo), float(hi)
    c_pt, d_pt = b_r - _INV_GOLDEN * (b_r - a_l), a_l + _INV_GOLDEN * (b_r - a_l)
    fc, fd = fn(c_pt), fn(d_pt)
    while (b_r - a_l) > _SQRT_EPS * max(1.0, abs(a_l), abs(b_r)):
        if fc > fd:
            b_r, d_pt, fd = d_pt, c_pt, fc
            c_pt = b_r - _INV_GOLDEN * (b_r - a_l)
            fc = fn(c_pt)
            continue
        a_l, c_pt, fc = c_pt, d_pt, fd
        d_pt = a_l + _INV_GOLDEN * (b_r - a_l)
        fd = fn(d_pt)
    mid = 0.5 * (a_l + b_r)
    return max(((c_pt, fc), (d_pt, fd), (mid, fn(mid))), key=lambda item: item[1])


def bucket_feature_value(val: Any) -> str:
    """Pin power-of-two bucketing for finite numeric features; keep bools and strings verbatim."""
    if val is None:
        return "__missing__"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        x = float(val)
        if not math.isfinite(x):
            return "__nonfinite__"
        return "0" if x == 0.0 else f"{'-' if x < 0.0 else ''}2^{int(math.floor(math.log2(abs(x))))}"
    return str(val)


def atom_mass(q: float) -> float:
    """Additive hazard mass m(a) = -ln(1 - q(a))."""
    return -math.log(1.0 - max(0.0, min(1.0 - _EPS, float(q))))


def _positive_masses(commit_masses: dict[str, float] | list[float]) -> list[float]:
    vals = commit_masses.values() if isinstance(commit_masses, dict) else commit_masses
    return [float(m) for m in vals if float(m) > 0.0]


def compose_vector_risk(commit_masses: dict[str, float] | list[float], phi: float = 0.0) -> float:
    """Commit-clustered risk p(V) = 1 - prod_c (1 + phi * m_{V,c})^(-1/phi) in [0, 1)."""
    pos = _positive_masses(commit_masses)
    if not pos:
        return 0.0
    p_val = max(0.0, float(phi))
    log_surv = -sum(pos) if p_val <= _SQRT_EPS else -(1.0 / p_val) * sum(math.log1p(p_val * m) for m in pos)
    if log_surv <= _MIN_LOG_FLOAT:
        return 1.0 - _EPS
    return max(0.0, min(1.0 - _EPS, -math.expm1(log_surv)))


def group_commit_masses(vector_commit_masses: list[dict[str, float]]) -> dict[str, float]:
    """Sum per-commit masses across vectors by commit ID so shared commits cluster once."""
    merged: dict[str, float] = {}
    for cid, mass in ((str(c), float(m)) for cm in vector_commit_masses for c, m in cm.items() if float(m) > 0.0):
        merged[cid] = merged.get(cid, 0.0) + mass
    return merged


def compose_change_risk(vector_commit_masses: list[dict[str, float]], phi: float = 0.0) -> float:
    """Whole-change risk grouped by commit ID across vectors before clustering."""
    return compose_vector_risk(group_commit_masses(vector_commit_masses), phi)


def invert_risk_to_mass(risk: float, phi: float = 0.0) -> float:
    """Exact inverse mass m = ((1 - p)^(-phi) - 1) / phi (Poisson limit -ln(1 - p))."""
    p = float(risk)
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        raise ValueError(f"risk must be strictly < 1.0, got {risk}")
    p_val = max(0.0, float(phi))
    return -math.log(1.0 - p) if p_val <= _SQRT_EPS else (math.pow(1.0 - p, -p_val) - 1.0) / p_val


def fit_clustering_phi(past_vectors: list[tuple[dict[str, float] | list[float], bool]]) -> float:
    """Exact 1D MLE of commit-level clustering variance phi >= 0 on past vectors (unbounded bracket)."""
    valid = [(cms, bool(y)) for raw, y in past_vectors if (cms := _positive_masses(raw))]
    if len(valid) < 2 or not any(y for _, y in valid) or all(y for _, y in valid):
        return 0.0

    def _ll(phi_val: float) -> float:
        return sum(
            math.log(pc if y else (1.0 - pc))
            for cms, y in valid
            for pc in (_clamp_prob(compose_vector_risk(cms, phi_val)),)
        )

    ll0 = _ll(0.0)
    hi = 1.0
    ll_hi = _ll(hi)
    while math.isfinite(hi * 2.0):
        nxt = _ll(hi * 2.0)
        if nxt <= ll_hi + _SQRT_EPS * max(1.0, abs(ll_hi)):
            break
        hi *= 2.0
        ll_hi = nxt
    best_x, best_ll = _golden_section_max(_ll, 0.0, hi * 2.0 if math.isfinite(hi * 2.0) else hi)
    return 0.0 if ll0 >= best_ll - _EPS * max(1.0, abs(best_ll)) else best_x


def _filter_closed_horizon(
    train_atoms: list[dict[str, Any]],
    horizon: float | None,
    max_order: float | None,
) -> tuple[list[dict[str, Any]], int]:
    indexed = sorted(
        ((float(a["order"]) if a.get("order") is not None else float(i), i, a) for i, a in enumerate(train_atoms)),
        key=lambda t: (t[0], str(t[2].get("commit", "")), str(t[2].get("atom_id", "")), t[1]),
    )
    if horizon is None or float(horizon) <= 0.0 or not indexed:
        return [a for _, _, a in indexed], 0
    if any(a.get("order") is None for _, _, a in indexed):
        raise ValueError("every train_atom must carry numeric 'order' when horizon is enforced")
    cutoff = (float(max_order) if max_order is not None else max(o for o, _, _ in indexed)) - float(horizon)
    closed = [a for o, _, a in indexed if o <= cutoff]
    return closed, len(indexed) - len(closed)


def _scalar_feature_keys(atoms: list[dict[str, Any]]) -> list[str]:
    return sorted({
        str(k)
        for a in atoms
        if isinstance(a.get("features"), dict)
        for k, v in a["features"].items()
        if not isinstance(v, (dict, list))
    })


def _atom_indicator_keys(ft: dict[str, Any], feat_keys: list[str]) -> tuple[list[tuple[str, str]], dict[str, str]]:
    bucketed = {k: bucket_feature_value(ft.get(k)) for k in feat_keys}
    keys = [("__bias__", ""), *((k, bucketed[k]) for k in feat_keys)]
    return keys, bucketed


def _adf_logistic_update(
    weights: dict[tuple[str, str], float],
    precs: dict[tuple[str, str], float],
    keys: list[tuple[str, str]],
    eta: float,
    var: float,
    y: int,
) -> None:
    """Exact rank-1 Laplace/ADF Gaussian conditioning projected onto marginal diagonal precisions."""
    p = _sigmoid(eta)
    grad = float(y) - p
    curv = max(_EPS, p * (1.0 - p))
    denom = 1.0 + curv * var
    for key in keys:
        hk = precs.get(key, 1.0)
        dk = 1.0 / hk
        weights[key] = weights.get(key, 0.0) + (dk / denom) * grad
        precs[key] = hk + curv / (1.0 + curv * max(0.0, var - dk))


def _summarize_feature_effects(
    feat_keys: list[str],
    weights: dict[tuple[str, str], float],
) -> list[dict[str, Any]]:
    effects: list[dict[str, Any]] = []
    for fk in feat_keys:
        vals = [abs(v) for (k, _), v in weights.items() if k == fk]
        if vals:
            effects.append({"feature": fk, "max_abs_log_odds": round(max(vals), 6), "bucket_count": len(vals)})
    effects.sort(key=lambda r: (-r["max_abs_log_odds"], r["feature"]))
    return effects


def fit_atom_risk_mixture(
    train_atoms: list[dict[str, Any]],
    candidate_atoms: list[dict[str, Any]],
    *,
    horizon: float | None = None,
    max_order: float | None = None,
    max_subset_order: int | None = None,
) -> dict[str, Any]:
    """Prequential BMA between constant KT and Additive Bayesian Logistic (rank-1 ADF + MacKay integral)."""
    _ = max_subset_order  # kept for backwards-compatible signature; additive model scales O(N * F)
    ordered_train, dropped_open = _filter_closed_horizon(train_atoms, horizon, max_order)
    feat_keys = _scalar_feature_keys(ordered_train)
    weights: dict[tuple[str, str], float] = {}
    precs: dict[tuple[str, str], float] = {}
    f0, n0 = 0, 0
    lw_const, lw_add = -math.log(2.0), -math.log(2.0)
    const_loss, add_loss, mix_loss = 0.0, 0.0, 0.0
    commit_preq_mass: dict[str, float] = {}
    commit_had_fault: dict[str, bool] = {}

    for a in ordered_train:
        ft = a.get("features") if isinstance(a.get("features"), dict) else {}
        keys, _ = _atom_indicator_keys(ft, feat_keys)
        y = 1 if bool(a.get("fault_within_horizon", a.get("fault", False))) else 0
        eta = sum(weights.get(k, 0.0) for k in keys)
        var = sum(1.0 / precs.get(k, 1.0) for k in keys)
        q_c = _clamp_prob((float(f0) + 0.5) / (float(n0) + 1.0))
        q_a = _clamp_prob(_sigmoid(eta / math.sqrt(1.0 + _PROBIT_SCALE * var))) if feat_keys else q_c
        z_cur = _logsumexp([lw_const, lw_add])
        p_mix = _clamp_prob(math.exp(lw_const - z_cur) * q_c + math.exp(lw_add - z_cur) * q_a)

        l_c = -math.log(q_c if y else (1.0 - q_c))
        l_a = -math.log(q_a if y else (1.0 - q_a))
        const_loss += l_c
        add_loss += l_a
        mix_loss += -math.log(p_mix if y else (1.0 - p_mix))
        lw_const -= l_c
        lw_add -= l_a
        cid = str(a.get("commit") or a.get("atom_id") or "")
        commit_preq_mass[cid] = commit_preq_mass.get(cid, 0.0) + atom_mass(p_mix)
        commit_had_fault[cid] = commit_had_fault.get(cid, False) or bool(y)
        f0 += y
        n0 += 1
        if feat_keys:
            _adf_logistic_update(weights, precs, keys, eta, var, y)

    z_fin = _logsumexp([lw_const, lw_add])
    w_c, w_a = math.exp(lw_const - z_fin), math.exp(lw_add - z_fin)
    q_c_fin = _clamp_prob((float(f0) + 0.5) / (float(n0) + 1.0))

    scored_atoms = []
    for idx_c, ca in enumerate(candidate_atoms):
        ft = ca.get("features") if isinstance(ca.get("features"), dict) else {}
        keys, bucketed = _atom_indicator_keys(ft, feat_keys)
        eta = sum(weights.get(k, 0.0) for k in keys)
        var = sum(1.0 / precs.get(k, 1.0) for k in keys)
        q_a_hat = _clamp_prob(_sigmoid(eta / math.sqrt(1.0 + _PROBIT_SCALE * var))) if feat_keys else q_c_fin
        q_a_hi = _clamp_prob(_sigmoid(eta + math.sqrt(var))) if feat_keys else q_c_fin
        q_hat = _clamp_prob(w_c * q_c_fin + w_a * q_a_hat)
        q_hi = _clamp_prob(w_c * q_c_fin + w_a * q_a_hi)
        m_hat = atom_mass(q_hat)
        g_mass = max(0.0, atom_mass(q_hi) - m_hat)
        contribs = {k: round(weights.get((k, bucketed[k]), 0.0), 6) for k in feat_keys}
        scored_atoms.append({
            "atom_id": str(ca.get("atom_id") or f"atom-{idx_c}"),
            "commit": str(ca.get("commit") or "HEAD"),
            "file": str(ca.get("file") or ""),
            "q": round(q_hat, 6),
            "mass": round(m_hat, 6),
            "epistemic_var": round(var, 6),
            "gap_mass": round(g_mass, 6),
            "feature_contributions": contribs,
        })

    n_train = len(ordered_train)
    mean_mix = (mix_loss / float(n_train)) if n_train else 0.0
    mean_const = (const_loss / float(n_train)) if n_train else 0.0
    mean_add = (add_loss / float(n_train)) if n_train else 0.0
    beats = bool(n_train > 0 and feat_keys and mean_mix < mean_const - _SQRT_EPS)
    effects = _summarize_feature_effects(feat_keys, weights)
    selected = [e["feature"] for e in effects if e["max_abs_log_odds"] > 0.0] if beats else []
    models = sorted(
        [
            {"model": "additive_logistic", "features": selected, "posterior_weight": round(w_a, 6), "mean_log_loss": round(mean_add, 6)},
            {"model": "constant_kt", "features": [], "posterior_weight": round(w_c, 6), "mean_log_loss": round(mean_const, 6)},
        ],
        key=lambda r: (-r["posterior_weight"], r["model"]),
    )
    return {
        "train_atoms_count": n_train,
        "dropped_open_horizon_atoms": dropped_open,
        "horizon_enforced": horizon,
        "mixture_mean_log_loss": round(mean_mix, 6),
        "constant_mean_log_loss": round(mean_const, 6),
        "beats_constant": beats,
        "selected_features": selected,
        "feature_effects": effects,
        "top_subsets": models,
        "scored_atoms": scored_atoms,
        "prequential_commit_vectors": [([m], commit_had_fault[cid]) for cid, m in commit_preq_mass.items()],
    }


def _git_out(repo: Path, args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode, proc.stdout


def _sha_matches(a: str, b: str) -> bool:
    al, bl = a.strip().lower(), b.strip().lower()
    return bool(al and bl) and (al.startswith(bl) or bl.startswith(al))


def _resolve_sha(ref: str, candidates: set[str]) -> str:
    low = ref.strip().lower()
    if not low:
        return ""
    if low in candidates:
        return low
    return next((s for s in candidates if s.lower().startswith(low) or low.startswith(s.lower())), "")


def _parse_numstat_line(line: str) -> tuple[str, int] | None:
    parts = line.split("\t", 2)
    if len(parts) != 3:
        return None
    add_s, del_s, path = parts
    return (path.strip(), int(add_s) + int(del_s)) if (add_s.isdigit() and del_s.isdigit()) else None


def _parse_numstat_log(raw: str) -> list[dict[str, Any]]:
    """Parse `git log --numstat --format=%x1e%H%x1f%s%x1f%b%x1d` cleanly even when commit bodies contain tabs."""
    commits: list[dict[str, Any]] = []
    for block in raw.split("\x1e"):
        if not block.strip() or "\x1d" not in block:
            continue
        header, numstat_part = block.split("\x1d", 1)
        h_parts = header.split("\x1f", 2)
        sha = h_parts[0].strip()
        subj = h_parts[1] if len(h_parts) > 1 else ""
        body = h_parts[2] if len(h_parts) > 2 else ""
        files = [parsed for ln in numstat_part.splitlines() if (parsed := _parse_numstat_line(ln)) is not None]
        commits.append({"sha": sha, "subject": subj, "msg": f"{subj}\n{body}", "files": files})
    return commits


def _extract_pre_spans(diff_txt: str) -> list[tuple[str, int, int]]:
    spans: list[tuple[str, int, int]] = []
    cur_file: str | None = None
    for line in diff_txt.splitlines():
        if line.startswith("--- "):
            cur_file = line[len("--- a/"):].strip() if line.startswith("--- a/") else None
            continue
        m = _HUNK_PRE_RE.match(line) if (cur_file and line.startswith("@@ ")) else None
        if not m:
            continue
        start = int(m.group(1))
        cnt = int(m.group(2)) if m.group(2) is not None else 1
        if start >= 1 and cnt >= 1:
            spans.append((cur_file, start, start + cnt - 1))
    return spans


def _blame_shas_for_span(repo: Path, fix_sha: str, fp: str, lo_l: int, hi_l: int, valid_shas: set[str]) -> set[str]:
    rc_b, bl_out = _git_out(repo, ["blame", "--porcelain", "-L", f"{lo_l},{hi_l}", f"{fix_sha}^", "--", fp])
    if rc_b != 0:
        return set()
    return {
        sha for ln in bl_out.splitlines()
        for sha in (ln.split(" ", 1)[0],)
        if _HEX_SHA_RE.match(sha) and sha in valid_shas and sha != fix_sha
    }


def _trace_fix_by_blame(repo: Path, fix_sha: str, valid_shas: set[str]) -> list[dict[str, Any]]:
    """Trace every deleted/modified hunk of `fix_sha` via `git blame` at `fix_sha^` to introducing commits."""
    rc_d, diff_txt = _git_out(repo, ["diff", "-U0", f"{fix_sha}^", fix_sha])
    if rc_d != 0:
        return []
    intro_files: dict[str, set[str]] = {}
    for fp, lo_l, hi_l in _extract_pre_spans(diff_txt):
        for sha in _blame_shas_for_span(repo, fix_sha, fp, lo_l, hi_l, valid_shas):
            intro_files.setdefault(sha, set()).add(fp)
    return [{"introducing_commit": i, "fix_commit": fix_sha, "files_touched": sorted(fps)} for i, fps in sorted(intro_files.items())]


def check_finder_diagnostics(
    repo: Path,
    pairs: list[dict[str, Any]],
    *,
    max_commits: int | None = None,
    slices: int = 4,
    rev: str = "HEAD",
) -> dict[str, Any]:
    """Raw mechanical finder diagnostics — reports measured numbers, zero boolean stability cutoffs."""
    log_args = ["log", "--reverse", "--format=%H%x1f%s%x1f%b%x1e", rev]
    if max_commits is not None:
        log_args.insert(2, f"-n{max(1, int(max_commits))}")
    rc, log_out = _git_out(repo, log_args)
    commits = [
        (parts[0], "\n".join(parts[1:]))
        for rec in (log_out.split("\x1e") if rc == 0 else [])
        if rec.strip()
        for parts in (rec.strip().split("\x1f", 2),)
    ]
    commit_set = {sha for sha, _ in commits}
    reverts = [
        (_resolve_sha(m.group(1), commit_set) or m.group(1).lower(), sha)
        for sha, body in commits
        if (m := _REVERT_SHA_RE.search(body))
    ]
    pair_keys = [(str(p.get("introducing_commit", "")), str(p.get("fix_commit", ""))) for p in pairs]
    fix_commits = [str(p.get("fix_commit", "")) for p in pairs if p.get("fix_commit")]
    recovered = sum(
        1 for tgt, rev_sha in reverts
        if any(_sha_matches(rf, rev_sha) and _sha_matches(ri, tgt) for ri, rf in pair_keys)
    )

    n_slices = max(1, min(int(slices), len(commits))) if commits else 0
    chunk = max(1, len(commits) // n_slices) if n_slices else 1
    slice_rates = []
    for idx in range(n_slices):
        sub = commits[idx * chunk : (None if idx == n_slices - 1 else (idx + 1) * chunk)]
        fixes = sum(1 for s, _ in sub if any(_sha_matches(fc, s) for fc in fix_commits))
        slice_rates.append({"slice": idx + 1, "commits": len(sub), "fixes": fixes, "rate": round(fixes / float(len(sub)), 6) if sub else 0.0})

    rates = [s["rate"] for s in slice_rates]
    nz_rates = [r for r in rates if r > 0.0]
    ratio = None if (not nz_rates or min(rates) == 0.0) else round(max(rates) / min(rates), 4)
    return {
        "commits_inspected": len(commits), "pairs_count": len(pairs),
        "reverts_checked": len(reverts), "reverts_recovered": recovered,
        "revert_recovery_rate": round(recovered / float(len(reverts)), 4) if reverts else None,
        "slice_fix_rates": slice_rates, "max_to_min_ratio": ratio,
        "level_status": "unverified",
    }


def _resolve_explicit_pairs(repo: Path, valid_shas: set[str], pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    for p in pairs:
        if p.get("introducing_commit") and p.get("fix_commit"):
            resolved.append(dict(p))
            continue
        if p.get("fix_commit"):
            f_full = _resolve_sha(str(p["fix_commit"]), valid_shas) or str(p["fix_commit"])
            resolved.extend(_trace_fix_by_blame(repo, f_full, valid_shas))
    return resolved


def _resolve_baseline_pairs(
    repo: Path,
    commits: list[dict[str, Any]],
    sha_to_idx: dict[str, int],
    pairs: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    valid_shas = set(sha_to_idx)
    if pairs is not None:
        return _resolve_explicit_pairs(repo, valid_shas, pairs)
    resolved: list[dict[str, Any]] = []
    for idx_c, c in enumerate(commits):
        m = _REVERT_SHA_RE.search(c["msg"])
        tgt = _resolve_sha(m.group(1), valid_shas) if m else ""
        if tgt:
            resolved.append({"introducing_commit": tgt, "fix_commit": c["sha"], "files_touched": [f for f, _ in c["files"]]})
            continue
        if idx_c > 0 and _BASELINE_FIX_RE.search(c["subject"]):
            resolved.extend(_trace_fix_by_blame(repo, c["sha"], valid_shas))
    return resolved


def _recent_touch_count(dq: deque[int], order_idx: int, horizon: int) -> int:
    while horizon > 0 and dq and (order_idx - dq[0]) > horizon:
        dq.popleft()
    return len(dq)


def _git_atom_features(
    sha: str, fp: str, lc: int, n_files: int, is_fix: bool, recent_n: int,
    touches: dict[str, int], file_faults: dict[str, int], dir_faults: dict[str, int],
    extra: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    feats: dict[str, Any] = {
        "lines_changed": lc,
        "files_in_commit": n_files,
        "is_new_file": touches.get(fp, 0) == 0,
        "is_fix_commit": is_fix,
        "recent_touches": recent_n,
        "file_prior_faults": file_faults.get(fp, 0),
        "dir_prior_faults": dir_faults.get(str(Path(fp).parent), 0),
        "prior_touches": touches.get(fp, 0),
    }
    if isinstance(extra.get(fp), dict):
        feats.update(extra[fp])
    atom_key = f"{sha}:{fp}"
    if isinstance(extra.get(atom_key), dict):
        feats.update(extra[atom_key])
    return feats


def _build_train_atoms(
    commits: list[dict[str, Any]],
    faulty_atoms: set[tuple[str, str]],
    horizon: int,
    extra: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int], dict[str, deque[int]], dict[str, int], dict[str, int]]:
    touches: dict[str, int] = {}
    recent_orders: dict[str, deque[int]] = {}
    file_faults: dict[str, int] = {}
    dir_faults: dict[str, int] = {}
    train_atoms: list[dict[str, Any]] = []
    flat = (
        (order_idx, c["sha"], len(c["files"]), bool(_BASELINE_FIX_RE.search(c["subject"])), fp, lc)
        for order_idx, c in enumerate(commits)
        for fp, lc in c["files"]
    )
    for order_idx, sha, n_files, is_fix, fp, lc in flat:
        dq = recent_orders.setdefault(fp, deque())
        recent_n = _recent_touch_count(dq, order_idx, horizon)
        is_fault = (sha, fp) in faulty_atoms
        train_atoms.append({
            "atom_id": f"{sha}:{fp}", "order": order_idx, "commit": sha, "file": fp,
            "features": _git_atom_features(sha, fp, lc, n_files, is_fix, recent_n, touches, file_faults, dir_faults, extra),
            "fault_within_horizon": is_fault,
        })
        touches[fp] = touches.get(fp, 0) + 1
        dq.append(order_idx)
        if is_fault:
            file_faults[fp] = file_faults.get(fp, 0) + 1
            dname = str(Path(fp).parent)
            dir_faults[dname] = dir_faults.get(dname, 0) + 1
    return train_atoms, touches, recent_orders, file_faults, dir_faults


def _build_candidate_atoms(
    cand_commits: list[dict[str, Any]],
    start_order: int,
    horizon: int,
    touches: dict[str, int],
    recent_orders: dict[str, deque[int]],
    file_faults: dict[str, int],
    dir_faults: dict[str, int],
    extra: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build candidate atoms chronologically so each commit sees strictly its parent state."""
    c_touches = dict(touches)
    c_recent = {fp: deque(dq) for fp, dq in recent_orders.items()}
    atoms: list[dict[str, Any]] = []
    flat = (
        (start_order + offset, c["sha"], len(c["files"]), bool(_BASELINE_FIX_RE.search(c["subject"])), fp, lc)
        for offset, c in enumerate(cand_commits)
        for fp, lc in c["files"]
    )
    for order_idx, sha, n_files, is_fix, fp, lc in flat:
        dq = c_recent.setdefault(fp, deque())
        recent_n = _recent_touch_count(dq, order_idx, horizon)
        atoms.append({
            "atom_id": f"{sha}:{fp}", "commit": sha, "file": fp,
            "features": _git_atom_features(sha, fp, lc, n_files, is_fix, recent_n, c_touches, file_faults, dir_faults, extra),
        })
        c_touches[fp] = c_touches.get(fp, 0) + 1
        dq.append(order_idx)
    return atoms


def _derive_default_horizon(pairs: list[dict[str, Any]], sha_to_idx: dict[str, int]) -> int:
    valid_shas = set(sha_to_idx)
    lags = [
        sha_to_idx[f_full] - sha_to_idx[i_full]
        for p in pairs
        for i_full in (_resolve_sha(str(p.get("introducing_commit", "")), valid_shas),)
        for f_full in (_resolve_sha(str(p.get("fix_commit", "")), valid_shas),)
        if i_full and f_full and sha_to_idx[f_full] > sha_to_idx[i_full]
    ]
    return int(statistics.median_high(lags)) if lags else 0


def extract_git_baseline(
    repo: Path,
    *,
    base: str = "",
    head: str = "HEAD",
    max_commits: int | None = None,
    horizon_commits: int | None = None,
    pairs: list[dict[str, Any]] | None = None,
    extra_features: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Universal codebase-agnostic git baseline trained strictly before `base` (when given)."""
    train_rev = base if base else head
    log_args = ["log", "--reverse", "--numstat", "--format=%x1e%H%x1f%s%x1f%b%x1d", train_rev]
    if max_commits is not None:
        log_args.insert(3, f"-n{max(1, int(max_commits))}")
    rc, raw = _git_out(repo, log_args)
    if rc != 0:
        raise ValueError(f"git log failed on {repo}")
    commits = _parse_numstat_log(raw)
    sha_to_idx = {c["sha"]: idx for idx, c in enumerate(commits)}
    valid_shas = set(sha_to_idx)
    resolved_pairs = _resolve_baseline_pairs(repo, commits, sha_to_idx, pairs)
    horizon = int(horizon_commits) if horizon_commits is not None else _derive_default_horizon(resolved_pairs, sha_to_idx)

    faulty_atoms: set[tuple[str, str]] = set()
    for p in resolved_pairs:
        i_full = _resolve_sha(str(p.get("introducing_commit", "")), valid_shas)
        f_full = _resolve_sha(str(p.get("fix_commit", "")), valid_shas)
        lag = (sha_to_idx[f_full] - sha_to_idx[i_full]) if (i_full and f_full) else 0
        if lag > 0 and (horizon == 0 or lag <= horizon):
            ft = p.get("files_touched") or [f for f, _ in commits[sha_to_idx[f_full]]["files"]]
            faulty_atoms.update((i_full, str(fp)) for fp in ft)

    extra = extra_features or {}
    train_atoms, touches, recent_orders, file_faults, dir_faults = _build_train_atoms(commits, faulty_atoms, horizon, extra)

    diff_spec = f"{base}..{head}" if base else (f"{head}^..{head}" if len(commits) > 1 else head)
    rc_d, diff_out = _git_out(repo, ["log", "--reverse", "--numstat", "--format=%x1e%H%x1f%s%x1f%b%x1d", diff_spec])
    cand_commits = _parse_numstat_log(diff_out) if rc_d == 0 else []
    candidate_atoms = _build_candidate_atoms(cand_commits, len(commits), horizon, touches, recent_orders, file_faults, dir_faults, extra)
    return {
        "source": "agent_finder" if pairs else "baseline_git",
        "horizon": horizon,
        "max_order": len(commits) - 1 if commits else 0,
        "train_atoms": train_atoms,
        "candidate_atoms": candidate_atoms,
        "finder_checks": check_finder_diagnostics(repo, resolved_pairs, max_commits=max_commits, rev=train_rev),
    }


def _atom_commit_mass_and_gap(item: Any, by_id: dict[str, dict[str, Any]]) -> tuple[str, float, float] | None:
    if isinstance(item, str) and item in by_id:
        rec = by_id[item]
        return rec["commit"], float(rec["mass"]), float(rec.get("gap_mass", 0.0))
    if isinstance(item, dict):
        cid = str(item.get("commit") or "HEAD")
        m = float(item["mass"]) if item.get("mass") is not None else atom_mass(float(item.get("q", 0.0)))
        gm = float(item.get("gap_mass", 0.0) or 0.0)
        return (cid, m, gm) if (m > 0.0 or gm > 0.0) else None
    return None


def _vector_commit_and_gap_masses(
    vec: dict[str, Any],
    by_id: dict[str, dict[str, Any]],
    by_file: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, float], float]:
    explicit_gap = float(vec["gap_mass"]) if (vec.get("gap_mass") is not None and float(vec["gap_mass"]) >= 0.0) else None
    if isinstance(vec.get("commit_masses"), dict):
        cms = {str(c): float(m) for c, m in vec["commit_masses"].items() if float(m) > 0.0}
        return cms, (explicit_gap if explicit_gap is not None else 0.0)
    out: dict[str, float] = {}
    g_sum = 0.0
    if isinstance(vec.get("atoms"), list):
        triples = (_atom_commit_mass_and_gap(a, by_id) for a in vec["atoms"])
        for cid, m, gm in (t for t in triples if t is not None):
            out[cid] = out.get(cid, 0.0) + m
            g_sum += gm
        return out, (explicit_gap if explicit_gap is not None else g_sum)
    if isinstance(vec.get("files"), list):
        matched = (rec for f in vec["files"] for rec in by_file.get(str(f), ()))
        for rec in matched:
            out[rec["commit"]] = out.get(rec["commit"], 0.0) + float(rec["mass"])
            g_sum += float(rec.get("gap_mass", 0.0))
        return out, (explicit_gap if explicit_gap is not None else g_sum)
    if vec.get("mass") is not None and float(vec["mass"]) > 0.0:
        out[str(vec.get("commit") or vec.get("name") or "vector")] = float(vec["mass"])
    return out, (explicit_gap if explicit_gap is not None else 0.0)


def _index_scored_atoms(
    scored_atoms: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    """Index by exact atom_id AND map every file path to ALL commits touching it in base..head."""
    by_id: dict[str, dict[str, Any]] = {}
    by_file: dict[str, list[dict[str, Any]]] = {}
    for sa in scored_atoms:
        by_id[sa["atom_id"]] = sa
        if sa["file"]:
            by_file.setdefault(sa["file"], []).append(sa)
    return by_id, by_file


def score_vectors(
    vectors: list[dict[str, Any]],
    *,
    train_atoms: list[dict[str, Any]] | None = None,
    candidate_atoms: list[dict[str, Any]] | None = None,
    horizon: float | None = None,
    max_order: float | None = None,
    past_vectors: list[dict[str, Any]] | None = None,
    phi: float | None = None,
    target: str = "traced_fix_within_horizon",
    finder_checks: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Score arbitrary vectors in [0, 1) with additive Bayesian model, epistemic gap mass, and commit grouping."""
    if target not in VALID_RISK_TARGETS:
        raise ValueError(f"target must be one of {VALID_RISK_TARGETS}, got {target!r}")
    mix_res = (
        fit_atom_risk_mixture(train_atoms, candidate_atoms, horizon=horizon, max_order=max_order)
        if (train_atoms is not None and candidate_atoms is not None)
        else None
    )
    by_id, by_file = _index_scored_atoms(mix_res["scored_atoms"]) if mix_res is not None else ({}, {})
    past_pairs = [
        (pv.get("commit_masses") or [float(pv.get("mass", 0.0))], bool(pv.get("had_fault", False)))
        for pv in (past_vectors or [])
    ]
    if not past_pairs and mix_res is not None:
        past_pairs = mix_res["prequential_commit_vectors"]
    phi_val = max(0.0, float(phi)) if phi is not None else fit_clustering_phi(past_pairs)

    prelim = [
        {
            "name": str(vec.get("name") or "vector"),
            "commit_masses": cms,
            "mass": sum(cms.values()),
            "gap_mass": g_mass,
            "risk": compose_vector_risk(cms, phi_val),
            "kind_scope_upper_bound": bool(vec.get("kind_scope_upper_bound", False)),
        }
        for vec in vectors
        for cms, g_mass in (_vector_commit_and_gap_masses(vec, by_id, by_file),)
    ]
    merged_commits = group_commit_masses([p["commit_masses"] for p in prelim])
    total_mass = sum(merged_commits.values())
    total_gap = sum(p["gap_mass"] for p in prelim)
    fc_out = dict(finder_checks) if isinstance(finder_checks, dict) else {"level_status": "unverified"}
    fc_out.setdefault("level_status", "unverified")

    gap_atoms = sorted(
        (mix_res["scored_atoms"] if mix_res is not None else []),
        key=lambda a: (-float(a.get("gap_mass", 0.0)), float(a.get("mass", 0.0)), a["atom_id"]),
    )
    return {
        "target": target, "phi": round(phi_val, 6),
        "change_mass": round(total_mass, 6),
        "change_gap_mass": round(total_gap, 6),
        "change_risk": round_risk(compose_vector_risk(merged_commits, phi_val)),
        "change_commit_masses": {c: round(m, 6) for c, m in sorted(merged_commits.items())},
        "finder_checks": fc_out,
        "feature_model": None if mix_res is None else {k: mix_res[k] for k in (
            "train_atoms_count", "dropped_open_horizon_atoms", "horizon_enforced",
            "mixture_mean_log_loss", "constant_mean_log_loss", "beats_constant",
            "selected_features", "feature_effects", "top_subsets",
        )},
        "gap_atoms": gap_atoms,
        "vectors": [
            {
                "name": p["name"], "risk": round_risk(p["risk"]), "mass": round(p["mass"], 6),
                "share": round(p["mass"] / total_mass, 6) if total_mass > 0.0 else 0.0,
                "gap_mass": round(p["gap_mass"], 6),
                "gap_share": round(p["gap_mass"] / total_gap, 6) if total_gap > 0.0 else 0.0,
                "phi": round(phi_val, 6),
                "commit_masses": {c: round(m, 6) for c, m in sorted(p["commit_masses"].items())},
                "target": target, "kind_scope_upper_bound": p["kind_scope_upper_bound"],
                "finder_checks": fc_out,
            }
            for p in prelim
        ],
    }


def _beta_binom_miss(k: int, a: float, b: float) -> float:
    val = 1.0
    for j in range(max(0, k)):
        val *= (a + float(j)) / max(_EPS, a + b + float(j))
    return val


def _solve_unit_exchangeable_alpha(k0: int, m0: float) -> float:
    """Unique a in (0, 1) solving prod_{j=0}^{k0-1} (a + j)/(1 + j) = m0 to IEEE-754 precision."""
    lo, hi = _EPS, 1.0 - _EPS
    while (hi - lo) > _EPS:
        mid = 0.5 * (lo + hi)
        if _beta_binom_miss(k0, mid, 1.0 - mid) < m0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _parse_anchor(anchor: Any) -> tuple[int, float, dict[str, Any]]:
    if not isinstance(anchor, dict):
        raise ValueError("anchored catch_table requires anchor={k, caught, total} or {k, miss}")
    k0 = int(anchor.get("k", 2))
    if k0 < 1:
        raise ValueError("anchor.k must be >= 1")
    if anchor.get("caught") is not None and anchor.get("total") is not None:
        caught_n, total_n = int(anchor["caught"]), int(anchor["total"])
        if total_n < 1 or caught_n < 0 or caught_n > total_n:
            raise ValueError("invalid anchor caught/total counts")
        missed_n = total_n - caught_n
        m0 = (float(missed_n) + 0.5) / (float(total_n) + 1.0)
        sd0 = math.sqrt((float(missed_n) + 0.5) * (float(caught_n) + 0.5) / (((total_n + 1.0) ** 2) * (total_n + 2.0)))
        return k0, m0, {"k": k0, "caught": caught_n, "total": total_n, "miss_mean": round(m0, 6), "miss_sd": round(sd0, 6)}
    if anchor.get("miss") is not None:
        m0 = _clamp_prob(float(anchor["miss"]))
        return k0, m0, {"k": k0, "miss_mean": round(m0, 6)}
    raise ValueError("anchor must specify (caught, total) or miss")


def _fill_measured_table(miss_by_k: dict[int, float] | None, max_k: int) -> tuple[dict[int, float | None], dict[int, float], dict[int, float], dict[int, float]]:
    if not miss_by_k:
        raise ValueError("measured catch_table requires non-empty miss_by_k")
    point: dict[int, float | None] = {0: 1.0}
    alloc: dict[int, float] = {0: 1.0}
    lo_m: dict[int, float] = {0: 1.0}
    hi_m: dict[int, float] = {0: 1.0}
    last_v = 1.0
    for k in range(1, max(max_k, max(int(x) for x in miss_by_k)) + 1):
        last_v = max(0.0, min(1.0, float(miss_by_k[k]))) if k in miss_by_k else last_v
        point[k] = alloc[k] = lo_m[k] = hi_m[k] = last_v
    return point, alloc, lo_m, hi_m


def _fill_anchored_table(anchor: Any, max_k: int) -> tuple[dict[int, float | None], dict[int, float], dict[int, float], dict[int, float], dict[str, Any]]:
    k0, m0, meta = _parse_anchor(anchor)
    a_int = _solve_unit_exchangeable_alpha(k0, m0)
    point: dict[int, float | None] = {0: 1.0}
    alloc: dict[int, float] = {0: 1.0}
    lo_m: dict[int, float] = {0: 1.0}
    hi_m: dict[int, float] = {0: 1.0}
    for k in range(1, max(max_k, k0) + 1):
        geom = math.pow(_clamp_prob(m0), float(k) / float(k0))
        point[k] = m0 if k == k0 else None
        lo_m[k], hi_m[k] = (m0, m0) if k == k0 else ((m0, geom) if k < k0 else (geom, m0))
        alloc[k] = _beta_binom_miss(k, a_int, 1.0 - a_int)
    return point, alloc, lo_m, hi_m, meta


def build_catch_table(
    provenance: str = "prior",
    *,
    miss_by_k: dict[int, float] | None = None,
    anchor: dict[str, Any] | None = None,
    max_k: int = 0,
) -> dict[str, Any]:
    """Catch table M(k) with sharp exchangeable brackets (NEVER reporting geometric lower bound as point)."""
    if provenance not in VALID_CATCH_PROVENANCE:
        raise ValueError(f"catch_table provenance must be one of {VALID_CATCH_PROVENANCE}, got {provenance!r}")
    anchor_meta: dict[str, Any] | None = None
    if provenance == "measured":
        point, alloc, lo_m, hi_m = _fill_measured_table(miss_by_k, max_k)
    elif provenance == "anchored":
        point, alloc, lo_m, hi_m, anchor_meta = _fill_anchored_table(anchor, max_k)
    else:
        ks = range(1, max(0, int(max_k)) + 1)
        point = {0: 1.0, **{k: None for k in ks}}
        lo_m = {0: 1.0, **{k: 0.0 for k in ks}}
        hi_m = {0: 1.0, **{k: 1.0 for k in ks}}
        alloc = {0: 1.0, **{k: _beta_binom_miss(k, 0.5, 0.5) for k in ks}}
    return {
        "provenance": provenance,
        "anchor": anchor_meta,
        "miss_by_k": {str(k): (None if v is None else round(v, 6)) for k, v in sorted(point.items())},
        "miss_bracket_by_k": {str(k): [round(lo_m[k], 6), round(hi_m[k], 6)] for k in sorted(point)},
        "_point": point, "_alloc": alloc, "_lo": lo_m, "_hi": hi_m,
    }


def catch_miss_at(catch_table: dict[str, Any], k: int) -> tuple[float | None, float, float, float]:
    """Return `(point_or_none, alloc_miss, lo_miss, hi_miss)` at panel size k."""
    kk = max(0, int(k))
    if kk in catch_table["_alloc"]:
        return catch_table["_point"][kk], catch_table["_alloc"][kk], catch_table["_lo"][kk], catch_table["_hi"][kk]
    prov = catch_table["provenance"]
    if prov == "prior":
        return None, _beta_binom_miss(kk, 0.5, 0.5), 0.0, 1.0
    if prov == "anchored" and isinstance(catch_table.get("anchor"), dict):
        k0, m0 = int(catch_table["anchor"]["k"]), float(catch_table["anchor"]["miss_mean"])
        geom = math.pow(_clamp_prob(m0), float(kk) / float(k0))
        a_int = _solve_unit_exchangeable_alpha(k0, m0)
        return None, _beta_binom_miss(kk, a_int, 1.0 - a_int), min(geom, m0), max(geom, m0)
    mx = max(catch_table["_alloc"])
    return catch_table["_point"][mx], catch_table["_alloc"][mx], catch_table["_lo"][mx], catch_table["_hi"][mx]


def residual_risk_with_bracket(
    commit_masses: dict[str, float],
    phi: float,
    k: int,
    catch_table: dict[str, Any],
) -> dict[str, Any]:
    """Per-vector residual risk (None off-anchor/prior) and sharp exchangeable bracket."""
    m_pt, _, m_lo, m_hi = catch_miss_at(catch_table, k)
    prov = str(catch_table["provenance"])
    r_pt = None if m_pt is None else round_risk(compose_vector_risk({c: m * m_pt for c, m in commit_masses.items()}, phi))
    r_lo = compose_vector_risk({c: m * m_lo for c, m in commit_masses.items()}, phi)
    r_hi = compose_vector_risk({c: m * m_hi for c, m in commit_masses.items()}, phi)
    return {
        "residual_risk": r_pt,
        "residual_risk_bracket": None if prov == "measured" else [round_risk(min(r_lo, r_hi)), round_risk(max(r_lo, r_hi))],
        "catch_table_provenance": prov,
    }


def change_residual_risk_with_bracket(
    vector_runs: list[tuple[dict[str, float], int]],
    phi: float,
    catch_table: dict[str, Any],
) -> dict[str, Any]:
    """Whole-change residual risk & bracket grouped by commit ID across vectors BEFORE clustering."""
    prov = str(catch_table["provenance"])
    pt_list: list[dict[str, float]] = []
    lo_list: list[dict[str, float]] = []
    hi_list: list[dict[str, float]] = []
    all_pts = True
    for cms, k in vector_runs:
        m_pt, _, m_lo, m_hi = catch_miss_at(catch_table, k)
        if m_pt is None:
            all_pts = False
        else:
            pt_list.append({c: m * m_pt for c, m in cms.items()})
        lo_list.append({c: m * m_lo for c, m in cms.items()})
        hi_list.append({c: m * m_hi for c, m in cms.items()})
    r_pt = round_risk(compose_change_risk(pt_list, phi)) if (all_pts and vector_runs) else None
    r_lo = compose_change_risk(lo_list, phi)
    r_hi = compose_change_risk(hi_list, phi)
    return {
        "change_residual_risk": r_pt,
        "change_residual_risk_bracket": None if prov == "measured" else [round_risk(min(r_lo, r_hi)), round_risk(max(r_lo, r_hi))],
        "catch_table_provenance": prov,
    }
