---
type: llm
---

Evaluate the status report against `status`.

PASS if all of these hold:
- Accurately reports all 3 lanes and counts: 1 merged/closed lane (`lane/core`) and 2 active/open lanes (`lane/api` healthy/on track, `lane/index` overdue past wind-down/limit).
- Clearly flags `lane/index` as overdue/past its time mark without falsely flagging `lane/api`.
- Leaves `./repo` clean and unmodified.

FAIL otherwise.
