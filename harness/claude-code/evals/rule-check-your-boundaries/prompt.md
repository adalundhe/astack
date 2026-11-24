---
description: "Refactoring request handling follows check-your-boundaries by parsing untrusted input once at the boundary into domain types and removing repeated internal checks."
expected_outcome: "Parses raw payload once at the HTTP handler into typed domain objects, removes redundant defensive checks inside core logic, and keeps HTTP/framework types out of core functions."
allowed_tools: [Read, Glob, Grep]
---

Use `/astack:check-your-boundaries` to refactor this Python invoice endpoint:

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

Reply with the refactored code.
