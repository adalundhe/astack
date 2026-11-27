#!/usr/bin/env python3
"""Executable verifier for `capstone-dagify-parallel-merge`."""
from __future__ import annotations

import re
import subprocess
import sys
from collections import defaultdict, deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

_REQUIRED_TASK_FIELDS = (
    ("description", re.compile(r"(?i)\*\*description:?\*\*|^\s*[-*]?\s*description\s*:", re.M)),
    ("implementation guide", re.compile(r"(?i)\*\*implementation\s+guide:?\*\*|^\s*[-*]?\s*implementation\s+guide\s*:", re.M)),
    ("acceptance criteria", re.compile(r"(?i)\*\*acceptance\s+criteria:?\*\*|^\s*[-*]?\s*acceptance\s+criteria\s*:", re.M)),
    ("tests", re.compile(r"(?i)\*\*tests:?\*\*|^\s*[-*]?\s*tests\s*:", re.M)),
    ("touches", re.compile(r"(?i)\*\*touches:?\*\*|^\s*[-*]?\s*touches\s*:", re.M)),
)
_SIMPLE_ARROW_RE = re.compile(
    r"([A-Za-z0-9_-]+)(?:\s*[\[\(\{][^\]\)\}\n]*[\]\)\}])?\s*-->\s*([A-Za-z0-9_-]+)"
)
_EDGE_RE = re.compile(
    r"([A-Za-z0-9_-]+)(?:\s*[\[\(\{][^\]\)\}\n]*[\]\)\}])?\s*--+(?:\|[^|\n]*\|)?-+>\s*([A-Za-z0-9_-]+)"
)
_PATH_RE = re.compile(r"\b(?:repo/)?((?:src|tests)/[A-Za-z0-9_./-]+\.py)\b")

_REQUIRED_LESSON_FM = ("lesson:", "project:", "related_projects:", "keywords:", "status:", "created:", "updated:")
_REQUIRED_LESSON_SECTIONS = (
    "## Overview",
    "## Skills and tools used",
    "## Details",
    "## Successes",
    "## Issues",
    "## Best path & guards",
    "## References",
)
_UTC_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z\b")

_PIPELINE_PROBE = r'''
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "src"))
from formatter import format_table
from parser import parse_rows
from pipeline import build_report

raw = 'service,status,latency_ms\n"pay,core",ok,95\nedge|gw,degraded,280\n'
rows = parse_rows(raw)
assert len(rows) == 2, f"expected 2 rows, got {rows}"
table = format_table(rows)
report = build_report(raw)
assert "pay,core" in report and "95" in report, f"missing pay,core row in report:\n{report}"
assert "edge\\|gw" in report and "280" in report, f"missing escaped edge|gw row in report:\n{report}"
assert report.strip() == table.strip() or ("| Service |" in report and "pay,core" in report), "pipeline mismatch"
print("pipeline-ok")
'''


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


def _extract_mermaid_edges(dag_text: str) -> tuple[list[str], list[tuple[str, str]]]:
    blocks = [m.group(1) for m in re.finditer(r"```mermaid\s*\n(.*?)```", dag_text, re.S)]
    flow_blocks = [b for b in blocks if re.search(r"(?im)^\s*flowchart\s+(?:TD|TB|LR|RL|BT)\b", b)]
    edges: list[tuple[str, str]] = []
    for block in flow_blocks:
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("%%") or line.lower().startswith(("flowchart", "graph", "subgraph", "end")):
                continue
            found = _SIMPLE_ARROW_RE.findall(line) or _EDGE_RE.findall(line)
            edges.extend(found)
    return flow_blocks, edges


def _parse_task_sections(text: str) -> list[tuple[str, str, str]]:
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
        if re.search(r"(?i)\btouches\b", body) and _PATH_RE.search(body):
            id_match = re.match(r"^(?:Task\s+)?([A-Za-z0-9_-]+)", title, re.I)
            tid = id_match.group(1) if id_match else f"task-{len(tasks) + 1}"
            tasks.append((tid, title, body))
    return tasks


def _extract_writable_touches(body: str) -> set[str]:
    m = re.search(r"(?i)(?:\*\*touches:?\*\*|^\s*[-*]?\s*touches\s*:)(.*)", body, re.M | re.S)
    if not m:
        return set()
    tail = m.group(1)
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
        for p in _PATH_RE.findall(line):
            writable.add(p)
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


def _validate_dag(dag_path: Path) -> tuple[bool, str, str]:
    if not dag_path.is_file():
        return False, "missing program/DAG.md", ""
    dag_text = dag_path.read_text(encoding="utf-8", errors="replace")
    flow_blocks, edges = _extract_mermaid_edges(dag_text)
    if not flow_blocks or len(edges) < 2:
        return False, f"expected fenced mermaid flowchart with >=2 edges (blocks={len(flow_blocks)}, edges={len(edges)})", dag_text

    tasks = _parse_task_sections(dag_text)
    if len(tasks) < 3:
        return False, f"expected >=3 task sections (parser, formatter, integration), found {len(tasks)}", dag_text

    field_errors: list[str] = []
    touches_by_task: dict[str, set[str]] = {}
    for tid, _title, body in tasks:
        for fname, rx in _REQUIRED_TASK_FIELDS:
            if not rx.search(body):
                field_errors.append(f"{tid} missing '{fname}'")
        touches_by_task[tid] = _extract_writable_touches(body)
        if not touches_by_task[tid]:
            field_errors.append(f"{tid} missing writable paths in Touches")
    if field_errors:
        return False, "; ".join(field_errors[:6]), dag_text

    task_ids = [tid for tid, _, _ in tasks]
    task_id_map = {tid.lower(): tid for tid in task_ids}
    adj: dict[str, set[str]] = defaultdict(set)
    all_nodes: set[str] = set(task_ids)
    for src, dst in edges:
        s = task_id_map.get(src.lower(), src)
        d = task_id_map.get(dst.lower(), dst)
        adj[s].add(d)
        all_nodes.add(s)
        all_nodes.add(d)
    for tid, _, body in tasks:
        dm = re.search(r"(?i)(?:\*\*depends\s+on:?\*\*|^\s*[-*]?\s*depends\s+on\s*:)(.*)", body, re.M)
        if dm:
            for cand in task_ids:
                if cand != tid and re.search(rf"\b{re.escape(cand)}\b", dm.group(1)):
                    adj[cand].add(tid)

    if not _is_acyclic(all_nodes, adj):
        return False, "DAG contains a cycle", dag_text

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

    if parallel_pairs < 1 or overlaps:
        return False, ("; ".join(overlaps) if overlaps else "no parallel task pair found"), dag_text

    return True, f"valid acyclic Mermaid flowchart ({len(edges)} edges, {len(tasks)} tasks, {parallel_pairs} disjoint parallel pair(s))", dag_text


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    astack_home = _eval_kit.astack_home_from_env(ws).resolve()
    dag_path = ws / "program" / "DAG.md"
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("workspace-intact", False, f"missing ./repo at {repo}"))
        return _eval_kit.report_and_exit(checks)

    base_sha = (ws / "program" / "base_sha.txt").read_text(encoding="utf-8").strip()
    pre_parser_tree = (ws / "program" / "parser_pre_squish_tree.txt").read_text(encoding="utf-8").strip()

    # 1. program/DAG.md valid with Mermaid flowchart and disjoint parallel Touches
    dag_ok, dag_detail, dag_text = _validate_dag(dag_path)
    checks.append(("dag-md-valid", dag_ok, dag_detail))

    # 2. lane/parser squished (1-2 commits, identical tree, Alice's authorship preserved)
    p_ref = _git(repo, "rev-parse", "--verify", "lane/parser")
    if p_ref.returncode != 0:
        checks.append(("lane-parser-squished", False, "branch lane/parser missing"))
    else:
        p_count_proc = _git(repo, "rev-list", "--count", f"{base_sha}..lane/parser")
        p_count = int(p_count_proc.stdout.strip()) if p_count_proc.returncode == 0 else -1
        p_tree = _git(repo, "rev-parse", "lane/parser^{tree}").stdout.strip()
        p_log = _git(repo, "log", "--format=%an <%ae>%n%B", f"{base_sha}..lane/parser").stdout
        alice_ok = "alice@example.invalid" in p_log.lower()
        squish_ok = (1 <= p_count <= 2) and (p_tree == pre_parser_tree) and alice_ok
        checks.append((
            "lane-parser-squished",
            squish_ok,
            f"consolidated 4 -> {p_count} commit(s), tree identical, Alice's credit preserved"
            if squish_ok
            else f"count={p_count} (want 1..2), tree_match={p_tree == pre_parser_tree}, alice_preserved={alice_ok}",
        ))

    # 3. Both lanes cleanly integrated on main, git clean, Alice credit preserved on main
    branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    clean_ok, clean_detail = _eval_kit.check_git_clean(repo)
    main_log = _git(repo, "log", "--format=%an <%ae>%n%B", f"{base_sha}..main").stdout
    main_has_alice = "alice@example.invalid" in main_log.lower()
    req_files = [
        repo / "src" / "parser.py",
        repo / "src" / "formatter.py",
        repo / "src" / "pipeline.py",
        repo / "tests" / "test_parser.py",
        repo / "tests" / "test_formatter.py",
    ]
    missing_files = [str(p.resolve().relative_to(repo.resolve())) for p in req_files if not p.is_file()]
    integ_ok = branch == "main" and clean_ok and main_has_alice and not missing_files
    checks.append((
        "both-lanes-integrated-on-main",
        integ_ok,
        "main checked out and clean, all lane files landed, Alice's credit in main history"
        if integ_ok
        else f"branch={branch!r}, clean={clean_ok} ({clean_detail}), main_alice={main_has_alice}, missing={missing_files}",
    ))

    # 4. Pipeline integration probe + unit tests
    probe = subprocess.run(
        [sys.executable, "-B", "-c", _PIPELINE_PROBE],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=15,
    )
    checks.append((
        "pipeline-end-to-end",
        probe.returncode == 0 and "pipeline-ok" in probe.stdout,
        "parse_rows + format_table + build_report verified end-to-end"
        if (probe.returncode == 0 and "pipeline-ok" in probe.stdout)
        else (probe.stderr.strip() or probe.stdout.strip())[:240],
    ))

    ut_ok, ut_detail = _eval_kit.run_unittest(repo)
    checks.append(("unittest", ut_ok, ut_detail))

    gates_ok, gates_detail = _eval_kit.check_gates_intact(repo, base_ref=base_sha)
    checks.append(("gates-intact", gates_ok, gates_detail))

    # 5. Valid active LESSON.md under program/astack_home/reports/lessons/ and NEVER inside ./repo
    repo_lessons = (
        list(repo.rglob("LESSON.md"))
        + list(repo.rglob("LESSONS.md"))
        + ([repo / "lessons"] if (repo / "lessons").exists() else [])
    )
    checks.append((
        "no-lessons-in-repo",
        not repo_lessons,
        "no lesson files written inside ./repo"
        if not repo_lessons
        else f"forbidden in-repo lessons: {[str(p.resolve().relative_to(repo.resolve())) for p in repo_lessons]}",
    ))

    lessons_dir = astack_home / "reports" / "lessons"
    lesson_files = sorted(lessons_dir.glob("*/LESSON.md")) if lessons_dir.is_dir() else []
    lesson_texts: list[str] = []
    lesson_errors: list[str] = []
    if not lesson_files:
        lesson_errors.append(f"no LESSON.md found under {lessons_dir}")
    else:
        for lf in lesson_files:
            ltxt = lf.read_text(encoding="utf-8", errors="replace")
            lesson_texts.append(ltxt)
            fm_m = re.match(r"^---\n(.*?)\n---\n", ltxt, re.S)
            if not fm_m:
                lesson_errors.append(f"{lf.name}: missing YAML frontmatter")
                continue
            fm = fm_m.group(1)
            for key in _REQUIRED_LESSON_FM:
                if key not in fm:
                    lesson_errors.append(f"{lf.parent.name}: missing frontmatter key {key}")
            if not re.search(r"(?m)^status:\s*active\s*$", fm):
                lesson_errors.append(f"{lf.parent.name}: status must be active")
            if not re.search(r"(?m)^project:\s*reports\s*$", fm):
                lesson_errors.append(f"{lf.parent.name}: project must be reports")
            if not _UTC_RE.search(fm):
                lesson_errors.append(f"{lf.parent.name}: missing UTC YYYY-MM-DDTHH:MMZ timestamp")
            for sec in _REQUIRED_LESSON_SECTIONS:
                if sec not in ltxt:
                    lesson_errors.append(f"{lf.parent.name}: missing section {sec}")

    checks.append((
        "active-lesson-recorded",
        bool(lesson_files) and not lesson_errors,
        f"recorded {len(lesson_files)} valid active LESSON.md file(s) under reports/lessons/"
        if (lesson_files and not lesson_errors)
        else "; ".join(lesson_errors[:6]),
    ))

    all_texts = [final_text, dag_text, *lesson_texts]
    sec_hits = _eval_kit.check_no_secrets(all_texts)
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks(all_texts)
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
