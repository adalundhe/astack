---
description: "Atomic outcome eval for show-the-states: inspects repo/src/order_fsm.py and writes a valid Mermaid stateDiagram-v2 diagram in program/STATES.md (or final_text) capturing all 5 order states (DRAFT, PENDING, PAID, FAILED, REFUNDED), exact transitions including PENDING -> FAILED -> PENDING retry and PAID -> REFUNDED, guards, and code citations while keeping ./repo clean."
expected_outcome: "Reads show-the-states/SKILL.md, inspects repo/src/order_fsm.py without modifying ./repo, produces a valid inline Mermaid stateDiagram-v2 diagram in program/STATES.md (and/or final_text) with all 5 states, start/end markers, exact transitions including retry (PENDING -> FAILED -> PENDING) and refund (PAID -> REFUNDED), no invented illegal transitions, and file:line citations."
timeout_seconds: 480
---

`/astack:go` Inspect the order lifecycle state machine in `./repo/src/order_fsm.py` without modifying `./repo`. Diagram its states, triggers, guards, and failure/retry paths in a valid Mermaid `stateDiagram-v2` chart grounded in `file:line` citations, writing the result to `program/STATES.md` and rendering the diagram inline in your response.
