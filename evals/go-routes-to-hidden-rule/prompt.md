---
description: "Go mode routes to a hidden rule skill by reading its SKILL.md on disk before reviewing a polling loop."
expected_outcome: "Reads the hidden event-driven SKILL.md file from disk without being told to read rules, and flags the polling loop with concrete event-driven guidance."
allowed_tools: [Read, Glob, Grep]
---

`/astack:go` Review this Python job waiter:

```python
import time

def wait_for_job(client, job_id: str):
    while True:
        status = client.get_status(job_id)
        if status in ("done", "failed"):
            return status
        time.sleep(2)
```
