"""Separated offline oracle for `lookback-and-lookup-lessons`."""
from __future__ import annotations

from pathlib import Path

_NEW_LESSON = """---
lesson: webhook-raw-body-hmac
project: billing
related_projects: [payments-gateway]
keywords: [webhook, hmac, stripe, json, raw-body, signature]
status: active
created: 2026-11-26T00:00Z
updated: 2026-11-26T00:00Z
---

# Verify webhook HMAC signatures over raw request bytes

## Overview
Compute and verify webhook HMAC signatures against the exact raw UTF-8 request body bytes before parsing JSON.
- **Applies when:** Verifying inbound signed webhooks in `billing` (including payloads delivered by `payments-gateway`) where retry deliveries may reorder JSON object keys.
- **Does not apply when:** Internal unsigned payloads that do not carry a body HMAC header.

## Skills and tools used
- **Skills:** `find-it`, `fix-it`, `lookback`
- **Tools / environments:** Python `unittest`, `openssl s_client`

## Details
Stripe webhook retries returned HTTP 400 after webhook timeout changes were deployed. The signature verifier hashed a re-serialized parsed JSON dict instead of the raw HTTP request bytes, so any change in JSON key ordering across retries invalidated the signature.

## Successes
- Disproved the initial TLS certificate expiry hypothesis early with `openssl s_client`.
- Fixed `repo/src/webhook.py` to hash raw UTF-8 request bytes prior to JSON parsing and added a regression test covering reordered JSON keys.

## Issues
- Initial investigation pursued TLS expiry before checking request body canonicalization differences on retries.

## Best path & guards
- **Next time:** On webhook 400 signature failures during retries, compare the raw payload bytes against the signed digest first.
- **Structural guards:** Keep raw-body byte access at the HTTP middleware boundary and retain the reordered-key HMAC regression test.

## References
- `repo/src/webhook.py`
- `program/session-log.md`
"""


def apply(ws: Path) -> dict[str, object]:
    astack_home = ws / "program" / "astack_home"
    lessons_root = astack_home / "billing" / "lessons"

    # Supersede the obsolete legacy-xml-parser lesson (repo/src/xml_parser.py was retired).
    stale_path = lessons_root / "legacy-xml-parser" / "LESSON.md"
    stale_text = stale_path.read_text(encoding="utf-8")
    stale_text = stale_text.replace("status: active", "status: superseded", 1)
    stale_text = stale_text.replace("updated: 2025-01-10T12:00Z", "updated: 2026-11-26T00:00Z", 1)
    stale_path.write_text(stale_text, encoding="utf-8")

    # Write the new durable lesson under ASTACK_HOME (never inside repo/).
    new_path = lessons_root / "webhook-raw-body-hmac" / "LESSON.md"
    new_path.parent.mkdir(parents=True, exist_ok=True)
    new_path.write_text(_NEW_LESSON, encoding="utf-8")

    return {
        "final_text": (
            "Captured the outage lesson at `program/astack_home/billing/lessons/webhook-raw-body-hmac/LESSON.md` "
            "(verifying HMAC signatures over raw UTF-8 request bytes before JSON parsing, linked to "
            "`payments-gateway`) and marked the obsolete `legacy-xml-parser` lesson as `superseded` because "
            "`repo/src/xml_parser.py` was retired. No lesson files were written inside `repo/`."
        ),
        "events": [],
    }
