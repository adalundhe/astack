"""Separated offline oracle for `skill-taskex`."""
from __future__ import annotations

import json
from pathlib import Path

_TASK_SCRIPT = '''#!/usr/bin/env python3
"""Recurring health-check watcher for ops-portal built on TaskEx."""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from taskex import (
    Env,
    RunStatus,
    SQLiteCheckpointStore,
    ShellProcess,
    TaskRunner,
    checkpoint,
    last_checkpoint,
    pause_point,
)

AUTOMATION_DIR = Path(__file__).resolve().parent
STATE_DB = AUTOMATION_DIR / "state" / "checkpoints.db"


async def run_health_pass(repo_dir: Path, dry_run: bool) -> dict[str, object]:
    prev = last_checkpoint()
    checks_completed = int(prev.state["checks_completed"]) if prev else 0
    await pause_point()
    script = repo_dir / "src" / "healthcheck.py"
    manifest = repo_dir / "src" / "services.json"
    if dry_run:
        state = {"checks_completed": checks_completed + 1, "mode": "dry-run", "target": str(manifest)}
        await checkpoint(state, metadata={"dry_run": True})
        return state

    config = Env(MERCURY_SYNC_EXECUTOR_TYPE="none")
    async with TaskRunner(config=config) as sub_runner:
        cmd_run = sub_runner.command(
            sys.executable,
            "-B",
            str(script),
            "--manifest",
            str(manifest),
            alias="ops_portal_health",
            cwd=str(repo_dir),
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            shell=False,
            timeout="30s",
        )
        res: ShellProcess = await sub_runner.wait(cmd_run.token)
        if res.status != RunStatus.COMPLETE:
            raise RuntimeError(f"healthcheck failed ({res.return_code}): {res.error}")
        state = {"checks_completed": checks_completed + 1, "output": str(res.result).strip()}
        await checkpoint(state, metadata={"ok": True})
        return state


async def main() -> int:
    parser = argparse.ArgumentParser(description="ops-portal TaskEx health watcher")
    parser.add_argument("--repo", default="./repo", help="Path to ops-portal repository")
    parser.add_argument("--once", action="store_true", help="Run a single bounded health check")
    parser.add_argument("--dry-run", action="store_true", help="Validate plan without mutating state")
    parser.add_argument("--resume", action="store_true", help="Resume from latest SQLite checkpoint")
    parser.add_argument("--clear-checkpoints", action="store_true", help="Remove saved checkpoints before running")
    parser.add_argument("--schedule", default="60s", help="Recurring schedule interval when not using --once")
    args = parser.parse_args()

    STATE_DB.parent.mkdir(parents=True, exist_ok=True)
    if args.clear_checkpoints and STATE_DB.exists():
        STATE_DB.unlink()

    repo_dir = Path(args.repo).resolve()
    config = Env(MERCURY_SYNC_EXECUTOR_TYPE="none")
    with SQLiteCheckpointStore(str(STATE_DB), max_checkpoints_per_run=50) as store:
        async with TaskRunner(config=config, checkpoint_store=store) as runner:
            prev = await runner.get_latest_task_checkpoint("health_watch") if args.resume else None
            if args.once or args.dry_run:
                run = runner.run(
                    run_health_pass,
                    repo_dir,
                    args.dry_run,
                    alias="health_watch",
                    timeout="30s",
                    resume_from=prev,
                )
            else:
                run = runner.run(
                    run_health_pass,
                    repo_dir,
                    False,
                    alias="health_watch",
                    schedule=args.schedule,
                    trigger="ON_START",
                    repeat="ALWAYS",
                    keep=10,
                    timeout="30s",
                    resume_from=prev,
                )
            res = await runner.wait(run.token)
            if res.status != RunStatus.COMPLETE:
                print(f"watcher failed ({res.status}): {res.error}", file=sys.stderr)
                return 1
            print(res.result)
            return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
'''


def apply(ws: Path) -> dict[str, object]:
    auto_dir = ws / "program" / "astack_home" / "ops-portal" / "automations" / "health-watcher"
    auto_dir.mkdir(parents=True, exist_ok=True)
    (auto_dir / "automation.json").write_text(
        json.dumps(
            {
                "runner": "taskex",
                "entrypoint": "task.py",
                "description": "Recurring ops-portal health-check watcher with SQLite checkpoints",
                "updated": "2026-11-26T09:00:00Z",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (auto_dir / "task.py").write_text(_TASK_SCRIPT, encoding="utf-8")
    (auto_dir / "config.example.json").write_text(
        json.dumps({"repo_path": "./repo", "schedule": "60s"}, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "final_text": (
            "Saved the ops-portal TaskEx health-check watcher under "
            "program/astack_home/ops-portal/automations/health-watcher/ (./repo left untouched).\n"
            "- Run once: `astack-tools python \"program/astack_home/ops-portal/automations/health-watcher/task.py\" --once --repo ./repo`\n"
            "- Resume: `astack-tools python \"program/astack_home/ops-portal/automations/health-watcher/task.py\" --once --resume --repo ./repo`"
        ),
    }
