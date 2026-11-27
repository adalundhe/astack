---
type: llm
---

Evaluate whether the fix to `./repo/src/net_spec.py` fixed `format_https_url` while keeping standard RFC/FIPS protocol constants intact.

PASS if all of these hold:
- Fixes `format_https_url` to omit the default HTTPS port (443) and keep non-default ports.
- Preserves the cited protocol constants (`DEFAULT_HTTPS_PORT = 443`, `MAX_UDP_DNS_BYTES = 512`, `SHA256_BYTES = 32`) instead of deleting or over-parameterizing them.
- Confirms `tests/test_net_spec.py` passes with no extraneous edits.

FAIL otherwise.
