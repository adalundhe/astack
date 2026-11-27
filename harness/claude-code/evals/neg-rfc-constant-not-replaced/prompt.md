---
description: "Negative control: fixing format_https_url in ./repo/src/net_spec.py preserves cited RFC and FIPS protocol constants (443, 512, 32) instead of misapplying constant removal to standard protocol values."
expected_outcome: "Fixes format_https_url to omit the default HTTPS port 443 while preserving DEFAULT_HTTPS_PORT=443, MAX_UDP_DNS_BYTES=512, and SHA256_BYTES=32 intact."
timeout_seconds: 240
---

`/astack:go` Fix `format_https_url` in `./repo/src/net_spec.py` so the default HTTPS port is omitted from the formatted URL while non-default ports are preserved, and ensure all tests in `./repo/tests/test_net_spec.py` pass.
