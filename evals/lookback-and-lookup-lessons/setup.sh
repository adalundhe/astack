#!/bin/bash
set -euo pipefail
mkdir -p program/astack_home/billing/lessons/legacy-xml-parser repo/src

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false

cat > repo/src/webhook.py <<'EOF'
def verify_signature(header: str, secret: str) -> bool:
    return bool(header and secret)
EOF
git -C repo add .
git -C repo commit -q -m "webhook json parser only; xml parser retired"

cat > program/astack_home/billing/lessons/legacy-xml-parser/LESSON.md <<'EOF'
---
lesson: legacy-xml-parser
project: billing
related_projects: []
keywords: [xml, parser]
status: active
created: 2025-01-10T12:00Z
updated: 2025-01-10T12:00Z
---

# Legacy XML parser flags

## Overview
Pass `--xml-compat` to `repo/src/xml_parser.py` before running billing imports.
- **Applies when:** Running `repo/src/xml_parser.py`.
- **Does not apply when:** N/A.

## Skills and tools used
- **Skills:** `find-it`
- **Tools / environments:** Python

## Details
Old XML parser needed `--xml-compat`.

## Successes
- Worked in 2025.

## Issues
- None.

## Best path & guards
- **Next time:** Pass `--xml-compat`.
- **Structural guards:** None.

## References
- `repo/src/xml_parser.py` (deleted in 2026)
EOF

cat > program/session-log.md <<'EOF'
# Completed Session Log (project: billing)

- Outage: Stripe webhook retries failed with 400 after deploying webhook timeout changes.
- Rejected theory: Initially suspected TLS expiry; `openssl s_client` disproved it.
- Root cause: Handler verified signature on parsed JSON dict instead of raw request bytes, breaking whenever key order changed across retries.
- Fix: Verified HMAC over raw UTF-8 request body before JSON parsing; added regression test with reordered keys.
- Related project: `payments-gateway` sends the signed webhooks.
EOF
