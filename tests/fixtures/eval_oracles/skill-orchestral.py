"""Separated offline oracle for `skill-orchestral`."""
from __future__ import annotations

import json
from pathlib import Path

_WORKFLOW_SCRIPT = '''#!/usr/bin/env python3
"""Multi-wave DAG workflow for data-sync built on Orchestral."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from orchestral import (
    Env,
    Orchestral,
    RunStatus,
    SQLiteCheckpointStore,
    WorkflowStatus,
    checkpoint,
    last_checkpoint,
    pause_point,
)

AUTOMATION_DIR = Path(__file__).resolve().parent
STATE_DB = AUTOMATION_DIR / "state" / "workflow.db"
STAGING_DIR = AUTOMATION_DIR / "state" / "staging"


async def extract_users(out_file: Path, dry_run: bool) -> dict[str, object]:
    await pause_point()
    rows = [{"user_id": "u1", "active": True}, {"user_id": "u2", "active": False}]
    if not dry_run:
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    payload = {"stage": "users", "count": len(rows), "path": str(out_file)}
    await checkpoint(payload)
    return payload


async def extract_orders(out_file: Path, dry_run: bool) -> dict[str, object]:
    await pause_point()
    rows = [{"order_id": "o1", "user_id": "u1", "amount": 4200}]
    if not dry_run:
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    payload = {"stage": "orders", "count": len(rows), "path": str(out_file)}
    await checkpoint(payload)
    return payload


async def reconcile_and_export(users_file: Path, orders_file: Path, summary_file: Path, dry_run: bool) -> dict[str, object]:
    prev = last_checkpoint()
    if prev and prev.state.get("exported"):
        return dict(prev.state)
    await pause_point()
    if dry_run:
        return {"exported": False, "dry_run": True, "matched_orders": 0}
    users = json.loads(users_file.read_text(encoding="utf-8"))
    orders = json.loads(orders_file.read_text(encoding="utf-8"))
    active_ids = {u["user_id"] for u in users if u.get("active")}
    matched = [o for o in orders if o.get("user_id") in active_ids]
    if not matched:
        skipped = {"exported": False, "reason": "no_active_orders", "matched_orders": 0}
        await checkpoint(skipped)
        return skipped
    summary = {"exported": True, "matched_orders": len(matched), "total_amount": sum(o["amount"] for o in matched)}
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    summary_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    await checkpoint(summary)
    return summary


async def main() -> int:
    parser = argparse.ArgumentParser(description="data-sync Orchestral DAG")
    parser.add_argument("--dry-run", action="store_true", help="Run without writing staging outputs")
    parser.add_argument("--show-waves", action="store_true", help="Print validated wave execution order and exit")
    parser.add_argument("--resume", action="store_true", help="Resume from saved SQLite checkpoints")
    parser.add_argument("--clear-checkpoints", action="store_true", help="Clear saved checkpoints before running")
    parser.add_argument("--fail-fast", action="store_true", default=True, help="Cancel downstream waves on error")
    args = parser.parse_args()

    STATE_DB.parent.mkdir(parents=True, exist_ok=True)
    if args.clear_checkpoints and STATE_DB.exists():
        STATE_DB.unlink()

    users_file = STAGING_DIR / "users.json"
    orders_file = STAGING_DIR / "orders.json"
    summary_file = STAGING_DIR / "summary.json"

    config = Env(MERCURY_SYNC_EXECUTOR_TYPE="none")
    with SQLiteCheckpointStore(str(STATE_DB)) as store:
        async with Orchestral(config=config, checkpoint_store=store, workflow_id="data-sync-dag") as orch:
            with orch as workflow:
                s_users = workflow.add_task(extract_users, users_file, args.dry_run, alias="extract_users", timeout="60s")
                s_orders = workflow.add_task(extract_orders, orders_file, args.dry_run, alias="extract_orders", timeout="60s")
                workflow.add_task(
                    reconcile_and_export,
                    users_file,
                    orders_file,
                    summary_file,
                    args.dry_run,
                    alias="reconcile_and_export",
                    dependencies=[s_users, s_orders],
                    timeout="60s",
                )

            waves = orch.execution_order()
            print("Waves:", waves)
            if args.show_waves:
                return 0

            if args.resume:
                await orch.resume(rerun_completed=False)
            else:
                await orch.run(wait=True, fail_fast=args.fail_fast, timeout="5m")

            if orch.status != WorkflowStatus.COMPLETED:
                print(f"workflow {orch.status.value}: {orch.error}", file=sys.stderr)
                return 1
            for name, runs in orch.results.items():
                for _, res in runs.items():
                    if res.status != RunStatus.COMPLETE:
                        print(f"step {name} ({res.status.value}): {res.error}", file=sys.stderr)
                        return 1
            return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
'''


def apply(ws: Path) -> dict[str, object]:
    auto_dir = ws / "program" / "astack_home" / "data-sync" / "automations" / "sync-dag"
    auto_dir.mkdir(parents=True, exist_ok=True)
    (auto_dir / "automation.json").write_text(
        json.dumps(
            {
                "runner": "orchestral",
                "entrypoint": "workflow.py",
                "workflow_id": "data-sync-dag",
                "description": "Two-wave data-sync DAG with explicit step state-passing and branching",
                "updated": "2026-11-26T09:00:00Z",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (auto_dir / "workflow.py").write_text(_WORKFLOW_SCRIPT, encoding="utf-8")
    return {
        "final_text": (
            "Saved the data-sync multi-wave Orchestral DAG under "
            "program/astack_home/data-sync/automations/sync-dag/ (./repo left untouched).\n"
            "- Validate waves: `astack-tools python \"program/astack_home/data-sync/automations/sync-dag/workflow.py\" --show-waves`\n"
            "- Run: `astack-tools python \"program/astack_home/data-sync/automations/sync-dag/workflow.py\" --dry-run`\n"
            "- Resume: `astack-tools python \"program/astack_home/data-sync/automations/sync-dag/workflow.py\" --resume`"
        ),
    }
