---
name: no-leaked-secrets
description: "Sweep code, diffs, configs, logs, errors, telemetry, tests, and debug artifacts for leaked secrets, tokens, credentials, unneeded personal data (PII), or excessive logging. Use when writing or reviewing code touching auth, config, logging, errors, telemetry, APIs, or before shipping."
---

# No leaked secrets

Never commit, expose, return, or log secrets, credentials, unneeded personal data, or noisy sensitive state.

## Start with

1. **Keep secrets out of code and artifacts.** Load API keys, passwords, private keys, tokens, signing salts, and connection strings from approved secret stores or runtime environment variables—never source files, defaults, fixtures, comments, or debug dumps.
2. **Minimize exposed data.** Return only fields the caller needs (**check-your-boundaries**). Strip internal IDs, raw credentials, tokens, session cookies, stack traces, and unneeded personal data (PII: emails, phone numbers, addresses, government IDs, payment details) from API responses, error payloads, and client bundles.
3. **Log narrowly and redact at the sink.** Log correlation IDs, status codes, and bounded summaries—never raw `Authorization`/`Cookie` headers, request/response bodies, `env` dumps, SQL parameters with user data, or full exception locals. Apply centralized redaction to structured logs, metrics labels, and trace spans.
4. **Sweep the full diff and working tree.** Before review or push, scan changed code, configs, tests, fixtures, and untracked files—and run **cleanup** if stray debug dumps or unredacted captures turn up.

## Watch for

- hardcoded keys, bearer/JWT tokens, private-key blocks, webhook secrets, or URLs with embedded credentials;
- `print`/`console.log`/`logger.debug` dumping whole requests, headers, env vars, user records, or config objects;
- trace spans, metric tags, or error messages interpolating tokens, emails, PII, or raw payloads;
- overly broad API serializers (e.g., returning whole DB rows/ORM models instead of explicit DTOs);
- secrets or real customer data copied into unit tests, snapshots, examples, or `<file>_DEBUG_<shorthash>.<type>` captures (**find-it**);
- temporary debug logging left enabled in production paths.

**The test:** if this file, log line, error message, metric, or API response were posted publicly tomorrow, would it expose a credential, personal data, or anything a caller didn't need? If yes, strip or redact it.

## When it doesn't fit

- explicitly synthetic, clearly invalid placeholder tokens in tests (e.g., `test-token-not-real`, `example.com`) that cannot authenticate anywhere;
- audited security/compliance logs whose required fields, retention, and access controls are documented in project policy.

**Showing it:** point to the exact `file:line` or runtime log/response output where the secret, token, PII, or unredacted payload appears, and show how it leaks across the boundary.

Referenced skills: `check-your-boundaries` (`../check-your-boundaries/SKILL.md`), `cleanup` (`../cleanup/SKILL.md`), `find-it` (`../find-it/SKILL.md`). Read any cited skill file before acting when its trigger applies.
