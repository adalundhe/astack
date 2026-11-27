"""Observable-class capture-recapture saturation for D > 0 blocking findings.

k = 2: Chapman (1951) + exact hypergeometric tail probability (and exact CI when caller sets `alpha`).
k >= 3: Burnham & Overton (1978, Biometrika 65(3):625-633) M_h Jackknife + Beta-Binomial M_h profile
        likelihood. All tolerances derive from IEEE-754 float64 (`sys.float_info.epsilon`, Brent 1973);
        all normal quantiles derive dynamically from `statistics.NormalDist().inv_cdf`.
"""
from __future__ import annotations

import math
import sys
from fractions import Fraction
from statistics import NormalDist
from typing import Any

_STD_NORMAL = NormalDist(0.0, 1.0)
_EPS = sys.float_info.epsilon
_SQRT_EPS = math.sqrt(_EPS)
_INV_GOLDEN = (math.sqrt(5.0) - 1.0) / 2.0

SATURATED_SCOPE_NOTE = (
    "These models stopped finding new blocking bugs. The remaining-bug estimate covers bugs of "
    "similar detectability to the ones already found; harder bugs or shared model blind spots "
    "cannot be ruled out by reviewer statistics alone."
)
UNCALIBRATED_CLEAN_SCOPE_NOTE = (
    "These models found no blocking bugs. Clean reviews mean these models found nothing, not proof "
    "that hard bugs or shared blind spots are absent."
)


def fmt_num(x: float | None) -> str:
    if x is None:
        return "unbounded"
    rounded = round(x, 2)
    return str(int(rounded)) if rounded == int(rounded) else f"{rounded:.2f}".rstrip("0").rstrip(".")


def _format_zero_observed(est: dict[str, Any]) -> str:
    if not est.get("calibrated"):
        return "none found yet (clean reviews alone cannot rule out harder bugs)"
    missed = est.get("jointly_missed_bugs") or []
    if est.get("joint_calibration") and missed:
        total = est.get("joint_bugs_evaluated", len(missed))
        miss_pct = round(float(est.get("empirical_joint_miss_rate", 0.0)) * 100.0)
        return f"none found yet (all models missed {len(missed)}/{total} calibration bug(s) — {miss_pct}% shared blind-spot miss rate)"
    if est.get("jeffreys_joint_miss_prob") is not None:
        miss_pct = round(float(est["jeffreys_joint_miss_prob"]) * 100.0)
        return f"none found yet (posterior miss ~{miss_pct}%)"
    return "none found yet (clean reviews alone cannot rule out harder bugs)"


def format_plain_range(est: dict[str, Any] | None) -> str:
    if est is None:
        return "unknown (fewer than two independent models completed this area)"
    if est.get("observed") == 0:
        return _format_zero_observed(est)
    pt = fmt_num(est["estimated_unfound"])
    lo = est.get("estimated_unfound_lower")
    hi = est.get("estimated_unfound_upper")
    if lo is None and hi is None:
        p_more = est.get("p_at_least_one_unfound")
        if p_more is None:
            return f"estimate ~{pt} more of similar detectability (no verified overlap yet)"
        return f"estimate ~{pt} more of similar detectability (p(>=1 unfound)={p_more:.3f})"
    if hi is None:
        prefix = f"at least {fmt_num(lo)}" if (lo or 0.0) > 0 else f"at least ~{pt}"
        return f"{prefix} more of similar detectability (upper bound unbounded — no verified overlap yet)"
    return f"about {pt} more of similar detectability (range {fmt_num(lo)}–{fmt_num(hi)})"


def _bb_log_lik(N: int, D: int, nz: list[tuple[int, int]], t: int, base: float, mu: float, u: float) -> float:
    f0 = N - D
    mu_c = max(_SQRT_EPS, min(1.0 - _SQRT_EPS, mu))
    log_t_fact = math.lgamma(t + 1)
    if u <= _SQRT_EPS:
        lm, l1 = math.log(mu_c), math.log(1.0 - mu_c)
        terms = sum(fj * (log_t_fact - math.lgamma(j + 1) - math.lgamma(t - j + 1) + j * lm + (t - j) * l1) for j, fj in nz)
        return base + f0 * t * l1 + terms
    conc = 1.0 / u
    a, b = mu_c * conc, (1.0 - mu_c) * conc
    log_denom = math.lgamma(a + b + t) + math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    terms = sum(fj * (log_t_fact - math.lgamma(j + 1) - math.lgamma(t - j + 1) + math.lgamma(a + j) + math.lgamma(b + t - j) - log_denom) for j, fj in nz)
    return base + f0 * (math.lgamma(a) + math.lgamma(b + t) - log_denom) + terms


def _golden_max(fn, lo: float, hi: float, tol: float) -> float:
    """Converge 1D unimodal maximum to relative/absolute width `tol`."""
    a_l, b_r = float(lo), float(hi)
    c_pt, d_pt = b_r - _INV_GOLDEN * (b_r - a_l), a_l + _INV_GOLDEN * (b_r - a_l)
    fc, fd = fn(c_pt), fn(d_pt)
    while (b_r - a_l) > tol * max(1.0, abs(a_l), abs(b_r)):
        if fc > fd:
            b_r, d_pt, fd = d_pt, c_pt, fc
            c_pt = b_r - _INV_GOLDEN * (b_r - a_l)
            fc = fn(c_pt)
            continue
        a_l, c_pt, fc = c_pt, d_pt, fd
        d_pt = a_l + _INV_GOLDEN * (b_r - a_l)
        fd = fn(d_pt)
    return max(fc, fd, fn(0.5 * (a_l + b_r)))


def _maximize_beta_binomial_ll(N: int, D: int, nz: list[tuple[int, int]], t: int, base: float) -> float:
    if (N - D) == 0 and len(nz) == 1 and nz[0][0] == t:
        return 0.0
    mu_lo, mu_hi = _SQRT_EPS, 1.0 - _SQRT_EPS
    mu_b = max(mu_lo, min(mu_hi, float(sum(j * fj for j, fj in nz)) / float(max(1, N * t))))
    tol_outer = math.sqrt(_SQRT_EPS)
    opt_mu = lambda u_val: _golden_max(lambda mu: _bb_log_lik(N, D, nz, t, base, mu, u_val), mu_lo, mu_hi, _SQRT_EPS)
    return max(_bb_log_lik(N, D, nz, t, base, mu_b, 0.0), opt_mu(1.0), _golden_max(opt_mu, 0.0, 1.0, tol_outer))


def _hypergeom_cdf_le(N: int, n1: int, n2: int, m: int) -> float:
    lo_x, hi_x = max(0, n1 + n2 - N), min(m, n1, n2)
    if lo_x > hi_x:
        return 0.0
    return sum(math.comb(n1, x) * math.comb(N - n1, n2 - x) for x in range(lo_x, hi_x + 1)) / math.comb(N, n2)


def _hypergeom_sf_ge(N: int, n1: int, n2: int, m: int) -> float:
    lo_x, hi_x = max(m, n1 + n2 - N), min(n1, n2)
    if lo_x > hi_x:
        return 0.0
    return sum(math.comb(n1, x) * math.comb(N - n1, n2 - x) for x in range(lo_x, hi_x + 1)) / math.comb(N, n2)


def _bisect_int(lo: int, hi: int, pred) -> int:
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if pred(mid):
            hi = mid
        else:
            lo = mid
    return hi


def _hypergeometric_lower(D: int, n1: int, n2: int, m: int, tail_prob: float) -> int:
    if _hypergeom_cdf_le(D, n1, n2, m) >= tail_prob:
        return D
    lo, hi = D, D + 1
    while _hypergeom_cdf_le(hi, n1, n2, m) < tail_prob:
        lo, hi = hi, D + (hi - D) * 2
    return _bisect_int(lo, hi, lambda mid: _hypergeom_cdf_le(mid, n1, n2, m) >= tail_prob)


def _hypergeometric_upper(D: int, n1: int, n2: int, m: int, tail_prob: float) -> int | None:
    if m == 0:
        return None
    lo, hi = D, D + 1
    while _hypergeom_sf_ge(hi, n1, n2, m) >= tail_prob:
        lo, hi = hi, D + (hi - D) * 2
    return _bisect_int(lo, hi, lambda mid: _hypergeom_sf_ge(mid, n1, n2, m) < tail_prob) - 1


def chapman_estimate(n1: int, n2: int, m: int, *, alpha: float | None = None) -> dict[str, Any]:
    """k = 2 Chapman (1951) point estimate, exact hypergeometric p-value, and optional (1-alpha) CI."""
    observed = n1 + n2 - m
    if n1 == 0 and n2 == 0:
        return {
            "estimator": "chapman_hypergeometric",
            "reviewers": 2, "n1": 0, "n2": 0, "m": 0, "observed": 0,
            "estimated_total": 0.0, "estimated_unfound": 0.0,
            "p_at_least_one_unfound": None, "confidence_alpha": alpha,
            "estimated_unfound_lower": None, "estimated_unfound_upper": None,
            "informative": False, "can_stop": False,
            "scope_note": UNCALIBRATED_CLEAN_SCOPE_NOTE,
        }
    total_frac = Fraction((n1 + 1) * (n2 + 1), m + 1) - 1
    unfound_frac = total_frac - observed
    p_one = _hypergeom_sf_ge(observed + 1, n1, n2, m) if m >= 1 else 1.0
    lower_u: float | None = None
    upper_u: float | None = None
    if alpha is not None:
        lower_N = _hypergeometric_lower(observed, n1, n2, m, alpha)
        upper_N = _hypergeometric_upper(observed, n1, n2, m, alpha)
        lower_u = max(0.0, float(lower_N - observed))
        upper_u = None if upper_N is None else max(0.0, float(upper_N - observed))
    can_stop = (m >= 1) and (upper_u is not None) and (upper_u < 1.0)
    return {
        "estimator": "chapman_hypergeometric",
        "reviewers": 2, "n1": n1, "n2": n2, "m": m, "observed": observed,
        "estimated_total": float(total_frac),
        "estimated_unfound": float(unfound_frac),
        "p_at_least_one_unfound": round(p_one, 6),
        "confidence_alpha": alpha,
        "estimated_unfound_lower": lower_u,
        "estimated_unfound_upper": upper_u,
        "informative": m >= 1,
        "can_stop": can_stop,
        "scope_note": SATURATED_SCOPE_NOTE,
    }


def _profile_ll_mle(freqs: list[int], t: int) -> tuple[int, float, Any]:
    """Unbounded unimodal MLE over N >= D via exponential bracketing + integer ternary search."""
    D = sum(freqs)
    sum_lg = sum(math.lgamma(fj + 1) for fj in freqs)
    nz = [(j + 1, fj) for j, fj in enumerate(freqs) if fj]
    cache: dict[int, float] = {}

    def prof_ll(N: int) -> float:
        if N not in cache:
            base = math.lgamma(N + 1) - math.lgamma(N - D + 1) - sum_lg
            cache[N] = _maximize_beta_binomial_ll(N, D, nz, t, base)
        return cache[N]

    lo, hi = D, D + 1
    while prof_ll(hi) > prof_ll(lo) + _SQRT_EPS * max(1.0, abs(prof_ll(lo))):
        lo, hi = hi, D + (hi - D) * 2
    left, right = max(D, D + (lo - D) // 2), hi
    while right - left > 2:
        m1 = left + (right - left) // 3
        m2 = right - (right - left) // 3
        if prof_ll(m1) < prof_ll(m2):
            left = m1
        else:
            right = m2
    best_N = max(range(left, right + 1), key=prof_ll)
    return best_N, prof_ll(best_N), prof_ll


def _beta_binomial_mh_ci(freqs: list[int], t: int, alpha: float, best_N: int, best_ll: float, prof_ll) -> tuple[float, float | None]:
    """Unbounded profile-likelihood CI over N >= D using exact bisection (zero arbitrary N cap)."""
    D = sum(freqs)
    if D == 0 or sum(freqs[1:]) == 0:
        return 0.0, None
    z_two = _STD_NORMAL.inv_cdf(1.0 - alpha / 2.0)
    thresh = best_ll - (z_two ** 2) / 2.0

    lower_N = D if prof_ll(D) >= thresh else _bisect_int(D, best_N, lambda mid: prof_ll(mid) >= thresh)

    lo_u, hi_u = best_N, best_N + 1
    prev_ll = prof_ll(lo_u)
    while prof_ll(hi_u) >= thresh:
        cur_ll = prof_ll(hi_u)
        if abs(prev_ll - cur_ll) <= _SQRT_EPS * max(1.0, abs(best_ll)) and hi_u > best_N + 1:
            return float(lower_N - D), None
        prev_ll = cur_ll
        lo_u, hi_u = hi_u, best_N + (hi_u - best_N) * 2
    upper_N = _bisect_int(lo_u, hi_u, lambda mid: prof_ll(mid) < thresh) - 1
    return float(lower_N - D), float(upper_N - D)


def _jackknife_coeffs(t: int, order: int) -> list[float]:
    """Exact polynomial coefficients from Burnham & Overton (1978), Table 1, Biometrika 65(3):625-633."""
    if order == 1:
        return [(t - 1) / t]
    if order == 2:
        return [(2 * t - 3) / t, -((t - 2) ** 2) / (t * (t - 1))]
    if order == 3:
        return [(3 * t - 6) / t, -(3 * t**2 - 15 * t + 19) / (t * (t - 1)), ((t - 3) ** 3) / (t * (t - 1) * (t - 2))]
    if order == 4:
        return [
            (4 * t - 10) / t,
            -(6 * t**2 - 36 * t + 55) / (t * (t - 1)),
            (4 * t**3 - 42 * t**2 + 148 * t - 175) / (t * (t - 1) * (t - 2)),
            -((t - 4) ** 4) / (t * (t - 1) * (t - 2) * (t - 3)),
        ]
    if order == 5:
        return [
            (5 * t - 15) / t,
            -(10 * t**2 - 70 * t + 125) / (t * (t - 1)),
            (10 * t**3 - 120 * t**2 + 485 * t - 660) / (t * (t - 1) * (t - 2)),
            -((t - 4) ** 5 - (t - 5) ** 5) / (t * (t - 1) * (t - 2) * (t - 3)),
            ((t - 5) ** 5) / (t * (t - 1) * (t - 2) * (t - 3) * (t - 4)),
        ]
    raise ValueError(f"unsupported jackknife order: {order}")


def _choose_jackknife_order(ests: list[tuple[int, float, float, list[float]]], freqs: list[int], t: int, alpha: float | None) -> int:
    D = sum(freqs)
    if alpha is None or D <= 1:
        return 0
    z_two = _STD_NORMAL.inv_cdf(1.0 - alpha / 2.0)
    chosen = 0
    for idx in range(len(ests) - 1):
        _, n1, _, c1 = ests[idx]
        _, n2, _, c2 = ests[idx + 1]
        b = [c2[j] - c1[j] for j in range(t)]
        s_b = sum(b[j] * freqs[j] for j in range(t))
        s_b2 = sum((b[j] ** 2) * freqs[j] for j in range(t))
        var_diff = (D / (D - 1)) * max(0.0, s_b2 - (s_b**2) / D)
        if var_diff <= 0 or abs(n2 - n1) / math.sqrt(var_diff) <= z_two:
            break
        chosen = idx + 1
    return chosen


def jackknife_mh_estimate(freq_counts: list[int], t: int, *, alpha: float | None = None) -> dict[str, Any]:
    """k >= 3 Burnham & Overton (1978) M_h Jackknife + Beta-Binomial M_h likelihood (optional alpha CI)."""
    if t < 3:
        raise ValueError("jackknife_mh_estimate requires t >= 3 reviewers")
    D, recaptured = sum(freq_counts), sum(freq_counts[1:])
    if D == 0:
        return {
            "estimator": "jackknife_mh", "reviewers": t, "order": 1,
            "frequencies": list(freq_counts), "observed": 0, "recaptured": 0,
            "estimated_total": 0.0, "estimated_unfound": 0.0, "se": 0.0,
            "p_at_least_one_unfound": None, "confidence_alpha": alpha,
            "estimated_unfound_lower": None, "estimated_unfound_upper": None,
            "informative": False, "can_stop": False,
            "scope_note": UNCALIBRATED_CLEAN_SCOPE_NOTE,
        }

    # Orders 1..5 are the complete closed-form table in Burnham & Overton (1978) Table 1
    ests = []
    for order in range(1, min(5, t - 1) + 1):
        a = _jackknife_coeffs(t, order)
        c = [1.0 + (a[j] if j < len(a) else 0.0) for j in range(t)]
        n_k = sum(c[j] * freq_counts[j] for j in range(t))
        var_k = max(0.0, sum((c[j] ** 2) * freq_counts[j] for j in range(t)) - n_k)
        ests.append((order, n_k, var_k, c))

    order, n_hat, var_hat, _ = ests[_choose_jackknife_order(ests, freq_counts, t, alpha)]
    n_hat, se = max(float(D), n_hat), math.sqrt(var_hat)
    u_hat = max(0.0, n_hat - D)

    best_N, best_ll, prof_ll = _profile_ll_mle(freq_counts, t)
    lr_one = max(0.0, 2.0 * (best_ll - prof_ll(D + 1))) if recaptured >= 1 else 0.0
    p_one = 1.0 if recaptured == 0 else (2.0 * (1.0 - _STD_NORMAL.cdf(math.sqrt(lr_one))))

    u_lower: float | None = None
    u_upper: float | None = None
    if alpha is not None:
        z_one = _STD_NORMAL.inv_cdf(1.0 - alpha)
        factor = math.exp(z_one * math.sqrt(math.log(1.0 + (se**2) / (u_hat**2)))) if (u_hat > 0 and se > 0) else 1.0
        j_lo = (u_hat / factor) if (u_hat > 0 and se > 0) else 0.0
        j_hi = (u_hat * factor) if (u_hat > 0 and se > 0) else max(0.0, u_hat + z_one * se)
        bb_lo, bb_hi = _beta_binomial_mh_ci(freq_counts, t, alpha, best_N, best_ll, prof_ll)
        u_lower = round(max(j_lo, bb_lo), 4)
        u_upper = None if bb_hi is None else round(max(j_hi, bb_hi), 4)

    informative = recaptured >= 1
    return {
        "estimator": "jackknife_mh", "reviewers": t, "order": order,
        "frequencies": list(freq_counts), "observed": D, "recaptured": recaptured,
        "estimated_total": round(n_hat, 4), "estimated_unfound": round(u_hat, 4), "se": round(se, 4),
        "p_at_least_one_unfound": round(p_one, 6), "confidence_alpha": alpha,
        "estimated_unfound_lower": u_lower, "estimated_unfound_upper": u_upper,
        "informative": informative,
        "can_stop": informative and (u_upper is not None) and (u_upper < 1.0),
        "scope_note": SATURATED_SCOPE_NOTE,
    }
