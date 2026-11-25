---
name: no-leaked-secrets
description: "Sweep code, diffs, configs, logs, errors, telemetry, tests, and debug artifacts for leaked secrets, credentials, unneeded personal data (PII), or excessive logging. Use before shipping or when touching auth, config, logging, errors, or APIs."
disable-model-invocation: true
---

# No leaked secrets

Never commit, expose, return, or log secrets, credentials, unneeded personal data, or sensitive internal state.

## Start with

1. **Keep secrets out of code and artifacts:** load API keys, passwords, private keys, tokens, salts, and connection strings from approved secret stores or runtime env vars. Never put them in source files, defaults, fixtures, comments, or debug dumps.
2. **Minimize exposed data (**check-your-boundaries**):** return only fields the caller needs. Strip internal IDs, credentials, tokens, cookies, stack traces, and unneeded PII (emails, phones, addresses, government IDs, payment details) from API responses, error payloads, and client bundles.
3. **Log narrowly and redact at the sink:** log correlation IDs, status codes, and bounded summaries. Never log `Authorization`/`Cookie` headers, raw request/response bodies, `env` dumps, SQL params with user data, or full exception locals. Apply centralized redaction to logs, metrics, and traces.
4. **Sweep the full diff and working tree:** before review or push, scan changed code, configs, tests, fixtures, and untracked files. Run **cleanup** if stray debug dumps turn up.

## Watch for

- hardcoded keys, bearer/JWT tokens, private-key blocks, webhook secrets, or URLs with embedded credentials;
- `print`/`console.log`/`logger.debug` dumping whole requests, headers, env vars, or user records;
- trace spans, metric tags, or errors interpolating tokens, emails, PII, or raw payloads;
- broad API serializers returning whole ORM models instead of explicit DTOs;
- real secrets or customer data copied into tests, snapshots, or `<file>_DEBUG_<shorthash>.<type>` captures (**find-it**);
- temporary debug logging left enabled in production paths.

**The test:** if this file, log line, error, metric, or API response went public tomorrow, would it leak a credential, PII, or unrequested internal data? If yes, strip or redact it.

## When it doesn't fit

- explicitly synthetic, clearly invalid placeholder tokens in tests (e.g., `test-token-not-real`, `example.com`) that cannot authenticate anywhere;
- audited compliance logs whose required fields, retention, and access controls are documented in policy.

**Showing it:** cite the exact `file:line` or runtime output where the secret, token, or PII leaks across the boundary.
