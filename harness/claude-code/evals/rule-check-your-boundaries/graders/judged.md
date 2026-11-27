---
type: llm
---

Evaluate the refactored webhook processor in `./repo` against `check-your-boundaries`.

PASS if all of these hold:
- Parses and validates untrusted payloads once at the entry point (`parse_webhook_payload` / `handle_webhook`) into typed domain dataclasses and returns explicit `400` error responses for malformed inputs.
- Core helpers (`calculate_subtotal`, `apply_discount`) accept the parsed domain dataclass instead of raw dicts and remove redundant `isinstance(..., dict)` / `.get()` re-checks.
- Adds unit tests verifying both valid payloads and rejected malformed boundary payloads.

FAIL otherwise.
