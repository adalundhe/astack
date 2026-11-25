---
name: no-leaked-secrets
description: "Sweep code, diffs, configs, logs, errors, tests, and debug artifacts for secrets, PII, or oversharing. Use before shipping or when touching auth, config, logging, errors, or APIs."
---

# No leaked secrets

Never commit, expose, return, or log secrets, credentials, unneeded personal data, or sensitive internal state.

## Start with

1. **Keep secrets out of code and artifacts**. Load keys, passwords, tokens, salts, and connection strings from secret stores or runtime env vars. Never put them in source, defaults, fixtures, or dumps, because leaked artifacts persist in git history.
2. **Minimize exposed data (`check-your-boundaries`):** return only fields the caller needs. Strip internal IDs, tokens, cookies, stack traces, and unneeded PII from API responses, errors, and client bundles.
3. **Log narrowly and redact at the sink**. Log correlation IDs, status codes, and bounded summaries. Never log auth headers, raw bodies, `env` dumps, or user SQL params, because logs spread widely. Redact centrally across logs, metrics, and traces.
4. **Sweep outgoing artifacts before review or push**. Scan diffs, commits, PR descriptions, proof attachments, configs, tests, and untracked files. Run **cleanup** if stray debug dumps turn up.
5. **Rotate and revoke first if a real secret already leaked:** whenever a live credential was committed, logged, or exposed, rotate and revoke it immediately before rewriting history or scrubbing files, because scrubbing does not invalidate an already-exposed key.

## Watch for

- hardcoded keys, bearer/JWT tokens, private-key blocks, webhook secrets, or URLs with embedded credentials;
- `print`/`console.log`/`logger.debug` dumping whole requests, headers, env vars, or user records;
- trace spans, metric tags, or errors interpolating tokens, emails, PII, or raw payloads;
- broad API serializers returning whole ORM models instead of explicit DTOs;
- real secrets or customer data copied into tests, snapshots, or `<file>_DEBUG_<shorthash>.<type>` captures (`find-it`);
- temporary debug logging left enabled in production paths.

**The test:** if this file, log, error, or response went public tomorrow, would it leak credentials or PII? If yes, strip or redact it.

## When it doesn't fit

- synthetic, clearly invalid placeholder tokens in tests (e.g. `test-token-not-real`, `example.com`) that cannot authenticate anywhere;
- audited compliance logs whose required fields, retention, and access controls are documented in policy.

**Showing it:** cite the exact `file:line` or runtime output where the secret, token, or PII leaks.

Referenced skills: `cleanup` (`../cleanup/SKILL.md`). Read any cited skill file before acting when its trigger applies.
