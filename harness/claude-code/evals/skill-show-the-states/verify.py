#!/usr/bin/env python3
"""Objective post-run verifier for skill-show-the-states."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

_CANONICAL_STATES = ("draft", "pending", "paid", "failed", "refunded")
_REQUIRED_EDGES = {
    ("*", "draft"),
    ("draft", "pending"),
    ("pending", "paid"),
    ("pending", "failed"),
    ("failed", "pending"),
    ("paid", "refunded"),
}
_FORBIDDEN_EDGES = {
    ("draft", "paid"),
    ("draft", "refunded"),
    ("refunded", "paid"),
    ("refunded", "pending"),
    ("refunded", "draft"),
}


def _collect_text(ws: Path) -> str:
    parts: list[str] = []
    md = ws / "program" / "STATES.md"
    if md.is_file():
        parts.append(md.read_text(encoding="utf-8", errors="replace").strip())
    ft = _eval_kit.final_text_from_env().strip()
    if ft:
        parts.append(ft)
    return "\n\n".join(p for p in parts if p)


def _canonicalize_state(raw_token: str, aliases: dict[str, str]) -> str | None:
    tok = raw_token.strip().strip('"').strip("'")
    if tok == "[*]":
        return "*"
    lookup = aliases.get(tok, tok)
    low = f"{tok} {lookup}".lower()
    for state in _CANONICAL_STATES:
        if re.search(rf"\b{state}\b", low) or state in low:
            return state
    return None


def _parse_state_diagram(block: str) -> tuple[set[str], set[tuple[str, str]]]:
    aliases: dict[str, str] = {}
    for m in re.finditer(r'^\s*state\s+"([^"]+)"\s+as\s+([A-Za-z0-9_]+)', block, re.M):
        aliases[m.group(2)] = m.group(1)

    states: set[str] = set()
    edges: set[tuple[str, str]] = set()
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("%%") or stripped.startswith("note "):
            continue
        m = re.match(r"^(\[\*\]|[A-Za-z0-9_]+)\s*-->\s*(\[\*\]|[A-Za-z0-9_]+)(?:\s*:\s*(.*))?$", stripped)
        if not m:
            continue
        src = _canonicalize_state(m.group(1), aliases)
        dst = _canonicalize_state(m.group(2), aliases)
        if src and src != "*":
            states.add(src)
        if dst and dst != "*":
            states.add(dst)
        if src and dst:
            edges.add((src, dst))
    return states, edges


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("repo-exists", False, f"missing repo directory: {repo}"))
        return _eval_kit.report_and_exit(checks)

    ok_clean, msg_clean = _eval_kit.check_git_clean(repo)
    checks.append(("repo-clean", ok_clean, msg_clean))

    combined = _collect_text(ws)
    low = combined.lower()
    mermaid_blocks = re.findall(r"```mermaid\s*\n(.*?)```", combined, re.S | re.I)
    state_blocks = [b for b in mermaid_blocks if re.search(r"^\s*stateDiagram-v2\b", b, re.M)]

    checks.append((
        "mermaid-stateDiagram-v2-present",
        bool(state_blocks),
        f"found {len(state_blocks)} stateDiagram-v2 Mermaid block(s)"
        if state_blocks
        else "missing fenced ```mermaid block starting with stateDiagram-v2 in program/STATES.md or final_text",
    ))

    all_states: set[str] = set()
    all_edges: set[tuple[str, str]] = set()
    for blk in state_blocks:
        st, ed = _parse_state_diagram(blk)
        all_states.update(st)
        all_edges.update(ed)

    missing_states = sorted(set(_CANONICAL_STATES) - all_states)
    checks.append((
        "all-five-states-present",
        not missing_states,
        "all 5 states represented (DRAFT, PENDING, PAID, FAILED, REFUNDED)"
        if not missing_states
        else f"missing states in stateDiagram-v2 transitions: {missing_states}",
    ))

    missing_edges = sorted(_REQUIRED_EDGES - all_edges)
    checks.append((
        "all-required-transitions-present",
        not missing_edges,
        "all required transitions verified including PENDING -> FAILED -> PENDING retry and PAID -> REFUNDED"
        if not missing_edges
        else f"missing required edges: {missing_edges}",
    ))

    illegal_edges = sorted(_FORBIDDEN_EDGES & all_edges)
    checks.append((
        "no-invented-illegal-transitions",
        not illegal_edges,
        "zero illegal shortcut transitions invented"
        if not illegal_edges
        else f"invented illegal transition(s): {illegal_edges}",
    ))

    cites_source = "order_fsm.py" in low
    cites_guards = (
        ("retry" in low or "attempts" in low or "max_attempts" in low)
        and ("refund" in low)
        and ("submit" in low or "items" in low)
    )
    checks.append((
        "grounded-in-source-and-guards",
        cites_source and cites_guards,
        f"cites_order_fsm={cites_source}, covers_guards_and_triggers={cites_guards}",
    ))

    sec_hits = _eval_kit.check_no_secrets([combined])
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks([combined])
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
