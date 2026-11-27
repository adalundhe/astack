---
description: "Renames a CLI flag (--format -> --output), changes the default format to jsonl, updates code and tests, and syncs all repo docs (README.md and docs/cli.md) with concrete verified examples and zero stale claims."
expected_outcome: "Reads technical-writing/SKILL.md, updates repo/src/export_cli.py and repo/tests/test_export_cli.py for --output (default jsonl), discovers and updates both repo/README.md and repo/docs/cli.md with zero remaining --format references or marketing fluff."
max_turns: 16
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Bash, Edit, Write]
---

`/astack:go` Update `./repo/src/export_cli.py` to rename the `--format` flag to `--output`, support `jsonl`, `json`, and `csv`, and change the default output format from `json` to `jsonl` (one JSON object per line). Update `./repo/tests/test_export_cli.py` for the new CLI behavior, and audit and update every affected documentation file in `./repo` so all commands, flags, defaults, and examples match the actual code with concrete, direct prose.
