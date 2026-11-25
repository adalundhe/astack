---
name: observable-by-default
description: "Make services, scheduled jobs, workers, queues, edge workloads, and infra operable at 3 AM with bounded-cardinality telemetry, trace correlation, symptom/SLO alerts, dead-letter visibility, and code-verified runbooks. Use when adding or reviewing services, jobs, queues, alerts, dashboards, or operational docs."
---

# Observable by default

Nothing important should fail silently—ship every service, scheduled job, queue, edge workload, and cutover with bounded-cardinality signals, actionable alerts, and a verified runbook so on-call can diagnose and recover fast.

Use whatever telemetry, logging, tracing, and alerting stack the repository runs (**analyze-environment**).

## Start with

1. **Instrument the right signals:**
   - **Services & edge:** golden signals (request rate, error rate by typed class, latency histograms, saturation of pools/queues/compute/memory).
   - **Scheduled jobs & async workers:** last-success timestamp (freshness/heartbeat), run duration, items processed/failed, retry counts, and dead-letter queue (DLQ) depth.
2. **Propagate context across boundaries:** carry trace/correlation IDs (e.g., `traceparent`, edge ray/request IDs, job IDs) through HTTP/RPC headers, queues, logs, and error reports—while redacting secrets and unnecessary PII (**no-leaked-secrets**).
3. **Keep metric cardinality bounded:** never put unbounded identifiers (`user_id`, `request_id`, high-scale `tenant_id`, raw URLs, ephemeral instance/pod UUIDs, or stack traces) into metric labels/tags; put high-cardinality fields in structured logs or trace attributes instead.
4. **Alert on symptoms, not noisy causes:** page on user-visible SLO burn, error rate, stuck queues, or missed job heartbeats—not transient CPU spikes. Every paging alert must name its user impact and link to a verified runbook.
5. **Ship a real runbook with the change (**technical-writing**):** document exact read-only health/verification commands, how to inspect stuck or failed work, how to safely replay/drain/rotate, and exact rollback steps—verified against the real code/environment (**prove-it**).

## Watch for

- scheduled jobs, background workers, or webhooks that log or swallow errors with no metric, alert, or DLQ visibility;
- metric labels containing unbounded IDs, emails, full URLs, or raw error strings (cardinality explosion);
- alerts firing on internal noise with no SLO impact or missing/stale runbook links;
- async consumers or edge/CDN hops dropping trace/correlation context so failures can't be traced end to end;
- migrations, auth/DNS/edge cutovers, or new services shipped without verification or rollback steps in the runbook.

**The test:** if this fails at 3 AM, how fast does on-call know, can they isolate the cause from telemetry without guessing, and does the runbook actually recover it?

## When it doesn't fit

- pure in-process helper libraries (surface typed errors and hooks for the caller to instrument rather than hardcoding a telemetry backend);
- one-off throwaway prototypes (**play-with-me**).

**Showing it:** trigger a real job failure, queue stall, or high-cardinality input and show either complete silence (no metric/alert/DLQ signal), exploding metric series, or a runbook command that fails against the real system.

Referenced skills: `analyze-environment` (`../analyze-environment/SKILL.md`), `no-leaked-secrets` (`../no-leaked-secrets/SKILL.md`), `technical-writing` (`../technical-writing/SKILL.md`), `prove-it` (`../prove-it/SKILL.md`), `play-with-me` (`../play-with-me/SKILL.md`). Read any cited skill file before acting when its trigger applies.
