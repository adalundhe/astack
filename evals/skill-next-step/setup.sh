#!/usr/bin/env bash
set -euo pipefail

mkdir -p program/astack_home/cli-kit/docs/contracts repo/src repo/docs

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/cli.py <<'EOF'
"""Minimal task runner CLI for cli-kit."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

DEFAULT_TASKS: dict[str, dict[str, str]] = {
    "lint": {"cmd": "ruff check src", "tag": "quality"},
    "test": {"cmd": "python3 -m unittest discover -s tests", "tag": "quality"},
    "package": {"cmd": "python3 -m build --wheel", "tag": "release"},
}


def load_tasks(config_path: str | None) -> dict[str, dict[str, str]]:
    resolved = config_path or os.environ.get("CLI_KIT_CONFIG", "").strip()
    if not resolved:
        return dict(DEFAULT_TASKS)
    data = json.loads(Path(resolved).read_text(encoding="utf-8"))
    return {str(k): dict(v) for k, v in data.items()}


def cmd_list(tasks: dict[str, dict[str, str]]) -> int:
    for name in sorted(tasks):
        meta = tasks[name]
        print(f"{name}\t[{meta.get('tag', 'general')}]\t{meta['cmd']}")
    return 0


def cmd_run(tasks: dict[str, dict[str, str]], task_name: str) -> int:
    if task_name not in tasks:
        print(f"error: unknown task {task_name!r}", file=sys.stderr)
        return 2
    print(f"RUN {task_name}: {tasks[task_name]['cmd']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cli-kit", description="Run named workspace tasks")
    parser.add_argument("--config", default=None, help="Path to JSON task catalog")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="List available tasks")
    run_p = sub.add_parser("run", help="Run a single named task")
    run_p.add_argument("task", help="Task name to execute")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    tasks = load_tasks(args.config)
    if args.command == "list":
        return cmd_list(tasks)
    if args.command == "run":
        return cmd_run(tasks, args.task)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
EOF

cat > repo/docs/user_feedback.md <<'EOF'
# User Feedback Notes — cli-kit

1. **CI scripting friction:** Engineers keep piping `cli-kit list` through `awk` and `cut` to extract task names and tags because `list` only emits tab-delimited text.
2. **No safe pre-flight preview:** Before running release tasks in CI, operators want to see the resolved command without executing it; today `cli-kit run <task>` always executes immediately.
3. **Repeated manual loops for tagged tasks:** Running all `quality` tasks requires manually chaining `cli-kit run lint && cli-kit run test`, even though every task already carries a `tag` field in `DEFAULT_TASKS`.
EOF

git -C repo add .
git -C repo commit -q -m "add cli-kit CLI and user feedback notes"

cat > program/astack_home/cli-kit/docs/contracts/cli-contract.md <<'EOF'
# cli-kit Contract Catalog (Tier 0)

Verified against `repo/src/cli.py`.

## Subcommands & Flags
- `cli-kit [--config <path>] list` — prints one tab-separated line per task (`<name>\t[<tag>]\t<cmd>`).
- `cli-kit [--config <path>] run <task>` — executes a single named task.

## Environment Variables
- `CLI_KIT_CONFIG` — optional fallback path to a JSON task catalog when `--config` is omitted.

## Exit Codes
- `0` — command succeeded.
- `1` — unexpected dispatch failure.
- `2` — unknown task name or argument parsing error.
EOF
