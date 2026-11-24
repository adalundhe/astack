---
description: "Writing a state-changing script follows safe-to-rerun with idempotent convergence, atomic write-then-rename, and crash-recovery tests."
expected_outcome: "Rewrites an append-only / in-place config updater to converge from current state, use atomic write-then-rename, handle stale temp/lock leftovers, and test double runs plus mid-run crashes."
allowed_tools: [Read, Glob, Grep]
---

Use `/astack:safe-to-rerun` to fix this Python deployment step:

```python
from pathlib import Path

def enable_feature(config_path: Path, feature: str) -> None:
    with config_path.open("a") as f:
        f.write(f"feature={feature}\n")
```

Reply with the fixed implementation and how you would test crash/rerun safety.
