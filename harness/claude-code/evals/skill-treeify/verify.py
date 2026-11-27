#!/usr/bin/env python3
"""Objective post-run verifier for skill-treeify."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

REQUIRED_LAYERS = ("tokens", "primitives", "composites", "pages")
REQUIRED_COMPONENTS = ("button", "textinput", "badge", "searchbar", "productcard", "catalogpage")
PATH_RE = re.compile(r"\b(?:repo/)?(src/(?:tokens|primitives|composites|pages)/[A-Za-z0-9_./-]+\.py)\b")


def _extract_mermaid_blocks(text: str) -> list[str]:
    return [m.group(1) for m in re.finditer(r"```mermaid\s*\n(.*?)```", text, re.S)]


def _wave_position(text: str, layer: str) -> int:
    """Return earliest character offset where a wave/layer heading introduces `layer`."""
    patterns = (
        re.compile(rf"(?im)^#{{2,4}}\s+.*wave\s*\d+.*\b{layer}\b.*$"),
        re.compile(rf"(?im)^#{{2,4}}\s+.*\b{layer}\b.*wave\s*\d+.*$"),
        re.compile(rf"(?im)^#{{2,4}}\s+.*\b{layer}\b.*$"),
    )
    for rx in patterns:
        m = rx.search(text)
        if m:
            return m.start()
    return -1


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    tree_path = ws / "program" / "TREE.md"
    final_text = _eval_kit.final_text_from_env()

    checks: list[tuple[str, bool, str]] = []

    ok_clean, msg_clean = _eval_kit.check_git_clean(repo)
    checks.append(("repo-clean", ok_clean, msg_clean))

    tree_exists = tree_path.is_file() and bool(tree_path.read_text(encoding="utf-8").strip())
    checks.append(("tree-file-exists", tree_exists, "program/TREE.md present" if tree_exists else "program/TREE.md missing or empty"))
    tree_text = tree_path.read_text(encoding="utf-8") if tree_exists else ""
    low = tree_text.lower()

    # Check Mermaid diagram
    mermaid_blocks = _extract_mermaid_blocks(tree_text)
    valid_mermaid = any(
        re.search(r"(?im)^\s*(?:flowchart|graph)\s+(?:TD|TB|LR|RL|BT)\b", b)
        and len(re.findall(r"-->|--->", b)) >= 4
        for b in mermaid_blocks
    )
    checks.append((
        "mermaid-diagram",
        valid_mermaid,
        f"valid Mermaid diagram with >=4 edges"
        if valid_mermaid
        else f"expected fenced ```mermaid flowchart/graph block with >=4 directed edges (found {len(mermaid_blocks)} block(s))",
    ))

    # Check all 4 layers and core components present
    missing_layers = [layer for layer in REQUIRED_LAYERS if layer not in low]
    norm_compact = re.sub(r"[^a-z0-9]", "", low)
    missing_comps = [c for c in REQUIRED_COMPONENTS if c not in norm_compact]
    checks.append((
        "layers-and-components-covered",
        not missing_layers and not missing_comps,
        "all 4 layers and 6 components covered"
        if (not missing_layers and not missing_comps)
        else f"missing layers={missing_layers}, components={missing_comps}",
    ))

    # Verify bottom-up wave ordering: tokens < primitives < composites < pages
    positions = {layer: _wave_position(tree_text, layer) for layer in REQUIRED_LAYERS}
    wave_order_ok = (
        all(pos >= 0 for pos in positions.values())
        and positions["tokens"] < positions["primitives"] < positions["composites"] < positions["pages"]
    )
    checks.append((
        "bottom-up-wave-order",
        wave_order_ok,
        f"bottom-up wave order verified (tokens@{positions['tokens']} < primitives@{positions['primitives']} < composites@{positions['composites']} < pages@{positions['pages']})"
        if wave_order_ok
        else f"layers not ordered tokens -> primitives -> composites -> pages (offsets: {positions})",
    ))

    # Per-component acceptance criteria count (expect >= 6 components or >= 4 distinct acceptance criteria blocks)
    ac_count = len(re.findall(r"(?i)(?:\*\*acceptance\s+criteria:?\*\*|^\s*[-*]?\s*acceptance\s+criteria\s*:)", tree_text, re.M))
    ac_ok = ac_count >= 5
    checks.append((
        "per-component-acceptance-criteria",
        ac_ok,
        f"found {ac_count} per-component acceptance criteria blocks"
        if ac_ok
        else f"expected >=5 per-component acceptance criteria blocks, found {ac_count}",
    ))

    # Writable paths span all 4 source layer dirs and stay disjoint across sibling component specs
    found_paths = sorted(set(PATH_RE.findall(tree_text)))
    covered_dirs = {p.split("/")[1] for p in found_paths}
    paths_ok = set(REQUIRED_LAYERS) <= covered_dirs and len(found_paths) >= 6
    checks.append((
        "disjoint-layer-paths",
        paths_ok,
        f"{len(found_paths)} component paths across all 4 layers"
        if paths_ok
        else f"expected >=6 component paths across {REQUIRED_LAYERS}, found {found_paths}",
    ))

    # Escalated verification: unit/isolated -> integration -> end-to-end
    has_unit = bool(re.search(r"\b(unit|isolated)\b", low))
    has_integration = "integration" in low
    has_e2e = bool(re.search(r"\b(end-to-end|e2e)\b", low))
    escalation_ok = has_unit and has_integration and has_e2e
    checks.append((
        "escalated-verification",
        escalation_ok,
        "testing escalates from isolated unit -> integration -> end-to-end"
        if escalation_ok
        else f"missing verification escalation (unit={has_unit}, integration={has_integration}, e2e={has_e2e})",
    ))

    sec = _eval_kit.check_no_secrets([tree_text, final_text])
    checks.append(("no-secrets", not sec, "; ".join(sec) if sec else "no secrets"))

    leaks = _eval_kit.check_no_internal_leaks([final_text])
    checks.append(("no-internal-leaks", not leaks, "; ".join(leaks) if leaks else "no internal leaks"))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
