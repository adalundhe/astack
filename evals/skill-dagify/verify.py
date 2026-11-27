#!/usr/bin/env python3
"""Objective post-run verifier for skill-dagify."""
from __future__ import annotations

import re
import sys
from collections import defaultdict, deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

REQUIRED_MODULES = (
    "src/parser.py",
    "src/validator.py",
    "src/storage.py",
    "src/cli.py",
)

REQUIRED_TASK_FIELDS = (
    ("description", re.compile(r"(?i)\*\*description:?\*\*|^\s*[-*]?\s*description\s*:", re.M)),
    ("implementation guide", re.compile(r"(?i)\*\*implementation\s+guide:?\*\*|^\s*[-*]?\s*implementation\s+guide\s*:", re.M)),
    ("acceptance criteria", re.compile(r"(?i)\*\*acceptance\s+criteria:?\*\*|^\s*[-*]?\s*acceptance\s+criteria\s*:", re.M)),
    ("tests", re.compile(r"(?i)\*\*tests:?\*\*|^\s*[-*]?\s*tests\s*:", re.M)),
    ("touches", re.compile(r"(?i)\*\*touches:?\*\*|^\s*[-*]?\s*touches\s*:", re.M)),
)

NODE_TOKEN_RE = re.compile(r"^\s*([A-Za-z0-9_-]+)")
EDGE_RE = re.compile(
    r"([A-Za-z0-9_-]+)(?:\s*[\[\(\{][^\]\)\}\n]*[\]\)\}])?\s*--+(?:\|[^|\n]*\|)?-+>\s*([A-Za-z0-9_-]+)"
)
SIMPLE_ARROW_RE = re.compile(
    r"([A-Za-z0-9_-]+)(?:\s*[\[\(\{][^\]\)\}\n]*[\]\)\}])?\s*-->\s*([A-Za-z0-9_-]+)"
)
PATH_RE = re.compile(r"\b(?:repo/)?((?:src|tests)/[A-Za-z0-9_./-]+\.py)\b")


def _extract_mermaid_blocks(text: str) -> list[str]:
    return [m.group(1) for m in re.finditer(r"```mermaid\s*\n(.*?)```", text, re.S)]


def _parse_mermaid_edges(block: str) -> list[tuple[str, str]]:
    edges: list[tuple[str, str]] = []
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("%%") or line.lower().startswith(("flowchart", "graph", "subgraph", "end")):
            continue
        found = SIMPLE_ARROW_RE.findall(line) or EDGE_RE.findall(line)
        for src, dst in found:
            edges.append((src, dst))
    return edges


def _parse_task_sections(text: str) -> list[tuple[str, str, str]]:
    """Return list of (task_id, heading, body) for markdown sections that define a task."""
    headings = list(re.finditer(r"^(#{2,4})\s+(.+?)\s*$", text, re.M))
    tasks: list[tuple[str, str, str]] = []
    for idx, m in enumerate(headings):
        level = len(m.group(1))
        title = m.group(2).strip()
        start = m.end()
        end = len(text)
        for nxt in headings[idx + 1:]:
            if len(nxt.group(1)) <= level:
                end = nxt.start()
                break
        body = text[start:end].strip()
        if re.search(r"(?i)\btouches\b", body) and PATH_RE.search(body):
            id_match = re.match(r"^(?:Task\s+)?([A-Za-z0-9_-]+)", title, re.I)
            tid = id_match.group(1) if id_match else f"task-{len(tasks)+1}"
            tasks.append((tid, title, body))
    return tasks


def _extract_writable_touches(body: str) -> set[str]:
    """Extract writable file paths from the Touches section of a task."""
    m = re.search(r"(?i)(?:\*\*touches:?\*\*|^\s*[-*]?\s*touches\s*:)(.*)", body, re.M | re.S)
    if not m:
        return set()
    tail = m.group(1)
    # Stop at next bold field label or subheading if present
    stop = re.search(
        r"\n\s*(?:#{2,4}\s+|[-*]?\s*\*\*(?:depends|dependencies|edges|description|implementation|acceptance|tests|review|notes)\b)",
        tail,
        re.I,
    )
    chunk = tail[:stop.start()] if stop else tail
    writable: set[str] = set()
    for line in chunk.splitlines():
        if re.search(r"(?i)\bread[- ]only\b|\bdo not modify\b|\bunmodified\b", line):
            continue
        for path in PATH_RE.findall(line):
            writable.add(path)
    return writable


def _reachable(adj: dict[str, set[str]], start: str) -> set[str]:
    seen: set[str] = set()
    q = deque(adj.get(start, ()))
    while q:
        cur = q.popleft()
        if cur in seen:
            continue
        seen.add(cur)
        q.extend(adj.get(cur, ()))
    return seen


def _is_acyclic(nodes: set[str], adj: dict[str, set[str]]) -> bool:
    indeg: dict[str, int] = {n: 0 for n in nodes}
    for u in nodes:
        for v in adj.get(u, ()):
            indeg[v] = indeg.get(v, 0) + 1
    q = deque(n for n, d in indeg.items() if d == 0)
    visited = 0
    while q:
        u = q.popleft()
        visited += 1
        for v in adj.get(u, ()):
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    return visited == len(indeg)


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    dag_path = ws / "program" / "DAG.md"
    final_text = _eval_kit.final_text_from_env()

    checks: list[tuple[str, bool, str]] = []

    ok_clean, msg_clean = _eval_kit.check_git_clean(repo)
    checks.append(("repo-clean", ok_clean, msg_clean))

    dag_exists = dag_path.is_file() and bool(dag_path.read_text(encoding="utf-8").strip())
    checks.append(("dag-file-exists", dag_exists, "program/DAG.md present" if dag_exists else "program/DAG.md missing or empty"))
    dag_text = dag_path.read_text(encoding="utf-8") if dag_exists else ""

    missing_mods = [m for m in REQUIRED_MODULES if m not in dag_text]
    checks.append((
        "all-modules-covered",
        not missing_mods,
        "all 4 modules covered" if not missing_mods else f"missing modules: {', '.join(missing_mods)}",
    ))

    mermaid_blocks = _extract_mermaid_blocks(dag_text)
    flowchart_blocks = [b for b in mermaid_blocks if re.search(r"(?im)^\s*flowchart\s+(?:TD|TB|LR|RL|BT)\b", b)]
    mermaid_edges: list[tuple[str, str]] = []
    for block in flowchart_blocks:
        mermaid_edges.extend(_parse_mermaid_edges(block))
    mermaid_ok = bool(flowchart_blocks) and len(mermaid_edges) >= 2
    checks.append((
        "mermaid-flowchart",
        mermaid_ok,
        f"valid Mermaid flowchart with {len(mermaid_edges)} edge(s)"
        if mermaid_ok
        else f"expected fenced ```mermaid flowchart block with >=2 edges (blocks={len(flowchart_blocks)}, edges={len(mermaid_edges)})",
    ))

    tasks = _parse_task_sections(dag_text)
    tasks_ok = len(tasks) >= 4
    checks.append((
        "task-count",
        tasks_ok,
        f"found {len(tasks)} task specs" if tasks_ok else f"expected >=4 task sections, found {len(tasks)}",
    ))

    field_errors: list[str] = []
    touches_by_task: dict[str, set[str]] = {}
    for tid, title, body in tasks:
        for fname, rx in REQUIRED_TASK_FIELDS:
            if not rx.search(body):
                field_errors.append(f"{tid} missing '{fname}'")
        touches_by_task[tid] = _extract_writable_touches(body)
        if not touches_by_task[tid]:
            field_errors.append(f"{tid} has no writable paths under Touches")
    checks.append((
        "per-task-required-fields",
        bool(tasks) and not field_errors,
        "all tasks include Description, Implementation guide, Acceptance criteria, Tests, and Touches"
        if (tasks and not field_errors)
        else "; ".join(field_errors[:6]) or "no tasks parsed",
    ))

    # Build DAG adjacency from Mermaid edges (and Depends on lines inside tasks)
    task_ids = [tid for tid, _, _ in tasks]
    task_id_map = {tid.lower(): tid for tid in task_ids}
    adj: dict[str, set[str]] = defaultdict(set)
    all_nodes: set[str] = set(task_ids)
    for src, dst in mermaid_edges:
        s = task_id_map.get(src.lower(), src)
        d = task_id_map.get(dst.lower(), dst)
        adj[s].add(d)
        all_nodes.add(s)
        all_nodes.add(d)

    for tid, _, body in tasks:
        dep_match = re.search(r"(?i)(?:\*\*depends\s+on:?\*\*|^\s*[-*]?\s*depends\s+on\s*:)(.*)", body, re.M)
        if dep_match:
            line = dep_match.group(1)
            for cand in task_ids:
                if cand != tid and re.search(rf"\b{re.escape(cand)}\b", line):
                    adj[cand].add(tid)

    acyclic = bool(all_nodes) and _is_acyclic(all_nodes, adj)
    checks.append((
        "dag-acyclic",
        acyclic,
        f"acyclic DAG across {len(all_nodes)} node(s)" if acyclic else "graph is empty or contains a cycle",
    ))

    # Verify parallel pairs exist and have strictly disjoint writable Touches
    reach = {tid: _reachable(adj, tid) for tid in task_ids}
    parallel_pairs = 0
    overlaps: list[str] = []
    for i in range(len(task_ids)):
        for j in range(i + 1, len(task_ids)):
            u, v = task_ids[i], task_ids[j]
            if v in reach[u] or u in reach[v]:
                continue
            parallel_pairs += 1
            shared = touches_by_task.get(u, set()) & touches_by_task.get(v, set())
            if shared:
                overlaps.append(f"{u} & {v} share {sorted(shared)}")

    disjoint_ok = parallel_pairs >= 1 and not overlaps
    checks.append((
        "parallel-touches-disjoint",
        disjoint_ok,
        f"{parallel_pairs} parallel task pair(s) with strictly disjoint writable paths"
        if disjoint_ok
        else ("; ".join(overlaps) if overlaps else "no parallel task pairs found (over-serialized graph)"),
    ))

    sec = _eval_kit.check_no_secrets([dag_text, final_text])
    checks.append(("no-secrets", not sec, "; ".join(sec) if sec else "no secrets"))

    leaks = _eval_kit.check_no_internal_leaks([final_text])
    checks.append(("no-internal-leaks", not leaks, "; ".join(leaks) if leaks else "no internal leaks"))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
