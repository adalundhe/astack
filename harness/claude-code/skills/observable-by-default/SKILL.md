---
name: observable-by-default
description: "Make services, scheduled jobs, workers, queues, edge workloads, and infra operable at 3 AM with bounded-cardinality telemetry, trace correlation, symptom/SLO alerts, dead-letter visibility, and verified runbooks."
disable-model-invocation: true
---

# Observable by default

Nothing important should fail silently. Ship every service, scheduled job, queue, edge workload, and cutover with bounded-cardinality signals, symptom alerts, and a verified runbook so on-call can recover fast.

Use whatever telemetry, logging, tracing, and alerting stack the repo already runs (**analyze-environment**).

## Start with

1. **Instrument the right signals:**
   - **Services & edge:** request rate, error rate by typed class, latency histograms, and pool/queue/CPU/memory saturation.
   - **Scheduled jobs & async workers:** last-success heartbeat, duration, items processed/failed, retries, and dead-letter queue (DLQ) depth.
2. **Propagate correlation context:** pass trace and request IDs (`traceparent`, edge ray IDs, job IDs) across HTTP/RPC headers, queues, logs, and errors. Strip secrets and unneeded PII (**no-leaked-secrets**).
3. **Keep metric cardinality bounded:** never put unbounded identifiers (`user_id`, `request_id`, high-scale `tenant_id`, raw URLs, pod UUIDs, stack traces) in metric labels, because cardinality explosions break metrics backends. Put those fields in structured logs or traces instead.
4. **Alert on symptoms, not noisy causes:** page on SLO burn, error rate, stuck queues, or missed heartbeats—never transient CPU blips. Every paging alert must state user impact and link to a verified runbook.
5. **Ship a verified runbook (**technical-writing**, **prove-it**):** include exact read-only health checks, stuck-work inspection, safe replay/drain steps, and rollback commands verified against the real system.

## Watch for

- scheduled jobs, workers, or webhooks that log errors with no metric, alert, or DLQ visibility;
- metric labels containing unbounded IDs, emails, full URLs, or raw error strings;
- alerts firing on internal noise or linking to stale runbooks;
- async consumers or edge hops dropping trace/correlation IDs;
- migrations, cutovers, or new services shipped with no verification or rollback runbook.

**The test:** if this fails at 3 AM, how fast does on-call know, can telemetry isolate the cause without guessing, and does the runbook actually recover it?

## When it doesn't fit

- pure in-process libraries (expose typed errors and hooks for callers to instrument instead);
- throwaway prototypes (**play-with-me**).

**Showing it:** trigger a job failure, queue stall, or high-cardinality input and show silence, exploding series, or a broken runbook command.

Referenced skills: `analyze-environment` (`${CLAUDE_SKILL_DIR}/../analyze-environment/SKILL.md`), `no-leaked-secrets` (`${CLAUDE_SKILL_DIR}/../no-leaked-secrets/SKILL.md`), `technical-writing` (`${CLAUDE_SKILL_DIR}/../technical-writing/SKILL.md`), `prove-it` (`${CLAUDE_SKILL_DIR}/../prove-it/SKILL.md`), `play-with-me` (`${CLAUDE_SKILL_DIR}/../play-with-me/SKILL.md`). Read any cited skill file before acting when its trigger applies.
