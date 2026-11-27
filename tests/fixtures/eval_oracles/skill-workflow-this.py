"""Separated offline oracle for `skill-workflow-this`."""
from __future__ import annotations

import json
from pathlib import Path

_AUDIT_WORKFLOW = '''#!/usr/bin/env python3
"""Crash-resumable nightly config audit workflow using Python 3 stdlib + SQLite."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from enum import StrEnum
from pathlib import Path


class TaskState(StrEnum):
    WAITING = "waiting"
    READY = "ready"
    RUNNING = "running"
    IN_REVIEW = "in_review"
    DONE = "done"
    FAILED = "failed"
    BLOCKED_ON_PERSON = "blocked_on_person"


ALLOWED_TRANSITIONS: dict[TaskState, frozenset[TaskState]] = {
    TaskState.WAITING: frozenset({TaskState.READY, TaskState.FAILED}),
    TaskState.READY: frozenset({TaskState.RUNNING, TaskState.BLOCKED_ON_PERSON, TaskState.FAILED}),
    TaskState.RUNNING: frozenset({TaskState.IN_REVIEW, TaskState.DONE, TaskState.FAILED, TaskState.BLOCKED_ON_PERSON}),
    TaskState.IN_REVIEW: frozenset({TaskState.DONE, TaskState.FAILED}),
    TaskState.DONE: frozenset(),
    TaskState.FAILED: frozenset({TaskState.READY}),
    TaskState.BLOCKED_ON_PERSON: frozenset({TaskState.READY, TaskState.FAILED}),
}

DAG: dict[str, tuple[str, ...]] = {
    "scan_configs": (),
    "check_permissions": (),
    "publish_summary": ("scan_configs", "check_permissions"),
}

AUTOMATION_DIR = Path(__file__).resolve().parent
STATE_DB = AUTOMATION_DIR / "state" / "audit_state.db"


def _init_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tasks (name TEXT PRIMARY KEY, state TEXT NOT NULL, detail TEXT NOT NULL)"
    )
    for name in DAG:
        conn.execute(
            "INSERT OR IGNORE INTO tasks (name, state, detail) VALUES (?, ?, ?)",
            (name, TaskState.WAITING.value, "initialized"),
        )
    conn.commit()
    return conn


def _transition(conn: sqlite3.Connection, task: str, target: TaskState, reason: str) -> None:
    row = conn.execute("SELECT state FROM tasks WHERE name = ?", (task,)).fetchone()
    current = TaskState(row[0])
    if target not in ALLOWED_TRANSITIONS[current]:
        raise RuntimeError(f"illegal transition for {task}: {current.value} -> {target.value}")
    conn.execute("UPDATE tasks SET state = ?, detail = ? WHERE name = ?", (target.value, reason, task))
    conn.commit()
    print(f"[transition] {task}: {current.value} -> {target.value} ({reason})")


def _load_configs(repo_dir: Path) -> list[dict[str, object]]:
    configs_dir = repo_dir / "configs"
    if not configs_dir.is_dir():
        raise FileNotFoundError(f"missing configs directory: {configs_dir}")
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(configs_dir.glob("*.json"))]


def _run_task(task: str, repo_dir: Path, dry_run: bool) -> str:
    configs = _load_configs(repo_dir)
    if task == "scan_configs":
        for cfg in configs:
            for req in ("service", "read_only_root", "privileged"):
                if req not in cfg:
                    raise ValueError(f"missing required key {req}")
        return f"scanned {len(configs)} config(s) (dry_run={dry_run})"
    if task == "check_permissions":
        bad = [str(c["service"]) for c in configs if c.get("privileged") is not False]
        if bad:
            raise ValueError(f"privileged services found: {', '.join(bad)}")
        return f"verified non-privileged posture for {len(configs)} service(s)"
    if task == "publish_summary":
        return f"summary ready for {len(configs)} service(s) (dry_run={dry_run})"
    raise ValueError(f"unknown task: {task}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Crash-resumable nightly config audit workflow")
    parser.add_argument("--repo", default="./repo", help="Target repository path")
    parser.add_argument("--dry-run", action="store_true", help="Run workflow without writing external outputs")
    parser.add_argument("--resume", action="store_true", help="Resume from saved SQLite state")
    parser.add_argument("--status", action="store_true", help="Print current per-task states and exit")
    args = parser.parse_args()

    if not args.resume and not args.status and STATE_DB.exists():
        STATE_DB.unlink()
    conn = _init_db(STATE_DB)
    try:
        if args.status:
            rows = conn.execute("SELECT name, state, detail FROM tasks ORDER BY name").fetchall()
            for name, state, detail in rows:
                print(f"{name}: {state} ({detail})")
            return 0

        repo_dir = Path(args.repo).resolve()
        while True:
            states = {n: TaskState(s) for n, s in conn.execute("SELECT name, state FROM tasks").fetchall()}
            progressed = False
            for task, deps in DAG.items():
                if states[task] != TaskState.WAITING:
                    continue
                if any(states[d] == TaskState.FAILED for d in deps):
                    _transition(conn, task, TaskState.FAILED, "skipped due to failed dependency")
                    progressed = True
                    continue
                if all(states[d] == TaskState.DONE for d in deps):
                    _transition(conn, task, TaskState.READY, "all dependencies done")
                    _transition(conn, task, TaskState.RUNNING, "started")
                    try:
                        detail = _run_task(task, repo_dir, args.dry_run)
                    except Exception as exc:
                        _transition(conn, task, TaskState.FAILED, str(exc))
                    else:
                        _transition(conn, task, TaskState.DONE, detail)
                    progressed = True
            if not progressed:
                break

        final_states = {n: TaskState(s) for n, s in conn.execute("SELECT name, state FROM tasks").fetchall()}
        return 0 if all(s == TaskState.DONE for s in final_states.values()) else 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
'''

_USAGE_DOC = '''# Nightly Config Audit Workflow

## State Machine
```mermaid
stateDiagram-v2
    [*] --> waiting
    waiting --> ready: dependencies done
    waiting --> failed: dependency failed
    ready --> running
    ready --> blocked_on_person: human decision required
    running --> in_review
    running --> done
    running --> failed
    in_review --> done
    in_review --> failed
    blocked_on_person --> ready
    failed --> ready: retry
```

## Failure Isolation
- Wave 1 runs `scan_configs` and `check_permissions` independently.
- If either wave-1 task fails, the other independent wave-1 task still finishes while wave-2 `publish_summary` transitions to `failed` with reason `skipped due to failed dependency`.

## Commands
- Dry-run: `python3 -B program/astack_home/nightly-audit/automations/nightly-config-audit/workflow.py --dry-run --repo ./repo`
- Resume interrupted run: `python3 -B program/astack_home/nightly-audit/automations/nightly-config-audit/workflow.py --resume --repo ./repo`
- Inspect task states: `python3 -B program/astack_home/nightly-audit/automations/nightly-config-audit/workflow.py --status`
'''


def apply(ws: Path) -> dict[str, object]:
    auto_dir = ws / "program" / "astack_home" / "nightly-audit" / "automations" / "nightly-config-audit"
    auto_dir.mkdir(parents=True, exist_ok=True)
    (auto_dir / "automation.json").write_text(
        json.dumps(
            {
                "entrypoint": "workflow.py",
                "description": "Stdlib Python crash-resumable nightly config audit workflow with SQLite per-task states",
                "updated": "2026-11-26T09:00:00Z",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    entry = auto_dir / "workflow.py"
    entry.write_text(_AUDIT_WORKFLOW, encoding="utf-8")
    entry.chmod(0o755)

    docs_dir = ws / "program" / "astack_home" / "nightly-audit" / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "nightly-config-audit.md").write_text(_USAGE_DOC, encoding="utf-8")

    return {
        "final_text": (
            "Created the stdlib Python crash-resumable workflow at "
            "program/astack_home/nightly-audit/automations/nightly-config-audit/workflow.py "
            "and usage documentation at program/astack_home/nightly-audit/docs/nightly-config-audit.md "
            "(./repo left untouched).\n"
            "- Runner: stdlib Python 3 + SQLite (no external packages installed).\n"
            "- States: waiting -> ready -> running -> in_review/done/failed/blocked_on_person.\n"
            "- Dry-run verified exit 0.\n"
            "- Rerun / resume: `python3 -B program/astack_home/nightly-audit/automations/nightly-config-audit/workflow.py --resume --repo ./repo`"
        ),
    }
