"""Internal Markdown coverage map formatter for `astack-review-ledger`."""
from __future__ import annotations

from typing import Any


def _fmt_residual(pt: float | None, bracket: list[float] | None) -> str:
    if pt is not None and bracket is not None:
        return f"{pt:.4f} [{bracket[0]:.4f}, {bracket[1]:.4f}]"
    if pt is not None:
        return f"{pt:.4f}"
    if bracket is not None:
        return f"[{bracket[0]:.4f}, {bracket[1]:.4f}]"
    return "—"


def format_markdown(result: dict[str, Any]) -> str:
    lines: list[str] = []
    hdr = f"# Review Coverage Map — {result['target']}" if result.get("target") else "# Review Coverage Map"
    lines.append(hdr)
    lines.append("")
    if result.get("landing_blocked"):
        lines.append("**LANDING BLOCKED** — unresolved blocking findings or incomplete risky coverage.")
        lines.append("")

    ra = result.get("risk_allocation") or {}
    if ra.get("budget_exceeded"):
        lines.append(
            f"**BUDGET OVERRUN** — planned wave cost `{ra['planned_cost']}` exceeds remaining budget "
            f"`{ra['remaining_budget']}` by `{ra['budget_overrun']}`."
        )
        lines.append("")

    ch_res = _fmt_residual(result.get("change_residual_risk"), result.get("change_residual_risk_bracket"))
    prov = result.get("catch_table_provenance", "prior")
    cal = result.get("scorer_calibration") or {}
    gap_str = f" | Dynamic gap share: `{cal.get('dynamic_gap_share', 0.0):.2f}`" if cal else ""
    lines.append(
        f"Overall: `{result['overall']}` | Change risk: `{result['change_risk']:.4f}` | "
        f"Residual ({prov}): `{ch_res}`{gap_str}"
    )
    if cal.get("miscalibrated_on_gaps"):
        lines.append("")
        lines.append("**SCORER MISCALIBRATED ON GAPS** — historical shares underperformed uniform/gap experts on past verified bugs.")
    lines.append("")

    if result.get("vectors"):
        lines.append("| Vector | Risk | Share | Residual | Reviews | Blockers | Action | Reason |")
        lines.append("|---|---:|---:|---|---:|---:|---|---|")
        for v in result["vectors"]:
            res_s = _fmt_residual(v.get("residual_risk"), v.get("residual_risk_bracket"))
            lines.append(
                f"| {v['name']} | {v['risk']:.4f} | {v['share']:.4f} | {res_s} | "
                f"{v['reviewers_completed']} | {v['observed_blockers']} | {v['action']} | {v['reason']} |"
            )
        lines.append("")

    if result.get("next_actions"):
        lines.append("## Next Actions")
        for act in result["next_actions"]:
            lines.append(f"- {act}")
        lines.append("")

    if result.get("could_not_test"):
        lines.append("## Could Not Check")
        for item in result["could_not_test"]:
            lines.append(f"- `{item.get('model', item.get('vector', 'unknown'))}`: {item.get('reason', '')}")
        lines.append("")

    return "\n".join(lines)
