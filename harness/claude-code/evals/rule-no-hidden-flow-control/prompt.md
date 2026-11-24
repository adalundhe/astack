---
description: "In Go mode, fixing a swallowed-exception loader routes to no-hidden-flow-control and replaces the catch-all with narrow catches and typed errors."
expected_outcome: "Reads no-hidden-flow-control/SKILL.md, removes `except Exception: return None`, catches specific exceptions narrowly, returns typed error values, and tests each failure path."
allowed_tools: [Read, Glob, Grep]
---

`/astack:go` Clean up this Python profile loader—when it fails in production we just get missing profiles with no idea what went wrong. Reply with the updated code and tests.

```python
import json
from pathlib import Path

def load_user_profile(path: Path) -> dict | None:
    try:
        raw = path.read_text()
        data = json.loads(raw)
        return {"id": int(data["id"]), "name": data["name"].strip()}
    except Exception:
        return None
```
