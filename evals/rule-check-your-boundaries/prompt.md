---
description: "In Go mode, refactoring a raw-dict endpoint routes to check-your-boundaries and parses untrusted input once at the edge."
expected_outcome: "Reads check-your-boundaries/SKILL.md, parses raw payloads once into typed domain objects at the handler boundary, and strips repeated defensive checks from core logic."
allowed_tools: [Read, Glob, Grep]
---

`/astack:go` Clean up this Python invoice endpoint—we're about to add several more fields and the defensive checks are getting messy. Reply with the refactored code.

```python
def calculate_total(payload: dict) -> float:
    if not payload or "items" not in payload or payload["items"] is None:
        raise ValueError("missing items")
    return sum(float(i["price"]) * int(i["qty"]) for i in payload["items"])

def apply_discount(payload: dict, total: float) -> float:
    code = payload.get("discount_code") if isinstance(payload, dict) else None
    if code == "SAVE10":
        return total * 0.9
    return total

def handle_request(http_request) -> dict:
    body = http_request.json()
    total = calculate_total(body)
    final = apply_discount(body, total)
    return {"status": 200, "total": final}
```
