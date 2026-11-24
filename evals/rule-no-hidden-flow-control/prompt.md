---
description: "Fixing error handling follows no-hidden-flow-control by removing broad catch-alls and swallowed exceptions in favor of narrow catches and typed error results."
expected_outcome: "Replaces broad `except Exception: return None` with narrow exception handling around I/O/parse calls, returns typed error values, and lets programming errors/interrupts propagate."
allowed_tools: [Read, Glob, Grep]
---

Use `/astack:no-hidden-flow-control` to fix this Python loader:

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

Reply with the fixed code and tests covering each failure path.
