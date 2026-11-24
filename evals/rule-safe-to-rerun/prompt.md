---
description: "In Go mode, fixing a deploy config-writer routes to safe-to-rerun and produces an idempotent, atomically renamed implementation with crash-recovery tests."
expected_outcome: "Reads safe-to-rerun/SKILL.md, converges from current file state, writes via temp file + atomic rename, handles stale leftovers, and tests double runs and mid-run crashes."
allowed_tools: [Read, Glob, Grep]
---

`/astack:go` Review and fix this deploy helper that enables feature flags on our app servers. Reply with the updated code and test plan.

```python
from pathlib import Path

def enable_feature(config_path: Path, feature: str) -> None:
    with config_path.open("a") as f:
        f.write(f"feature={feature}\n")
```
