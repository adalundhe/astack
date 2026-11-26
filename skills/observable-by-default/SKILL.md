---
name: observable-by-default
description: "Ship services, jobs, queues, and infra with bounded telemetry, trace IDs, SLO alerts, and verified runbooks. Use when building or operating services, jobs, queues, or cutovers."
disable-model-invocation: true
---

# Observable by default

Nothing important should fail silently. Ship services, jobs, queues, edge workloads, and cutovers with bounded signals, symptom alerts, and a verified runbook. On-call needs fast recovery without guessing.

Use the telemetry, logging, tracing, and alerting stack the repo already runs (**analyze-environment**). Save collected logs, traces, and metrics snapshots under `$HOME/.astack/<project_name>/logging/<logs|traces|metrics>/[FILE_YYYY_MM_DD_HH_MM_SS]` (`%USERPROFILE%\.astack\...` on Windows) via `astack-tools logging path`.

## Start with

1. **Instrument the right signals:**
   - **Services & edge:** request rate, typed error rate, latency histograms, and pool/queue/CPU/memory saturation.
   - **Scheduled jobs & workers:** last-success heartbeat, duration, items processed/failed, retries, and dead-letter queue (DLQ) depth.
2. **Propagate correlation context:** pass trace and job IDs (`traceparent`, ray IDs) across headers, queues, and logs. Shared IDs matter because cross-hop failures look unrelated without them. Strip secrets and unneeded PII (**no-leaked-secrets**).
3. **Keep metric cardinality bounded**. Never put unbounded IDs (`user_id`, `request_id`, raw URLs) in metric labels, because explosions break metrics backends. Put those fields in structured logs or traces instead.
4. **Alert on symptoms, not noisy causes:** page on SLO burn, error rate, stuck queues, or missed heartbeats. Skip transient CPU blips, because alert fatigue hides real outages. Every paging alert must state user impact and link to a verified runbook.
5. **Ship a verified runbook (`technical-writing`, `prove-it`):** include read-only health checks, stuck-work inspection, replay/drain steps, and rollback commands. Verify every command against the real system, because untested runbooks fail under pressure.

## Watch for

- scheduled jobs, workers, or webhooks logging errors with no metric, alert, or DLQ visibility;
- metric labels containing unbounded IDs, emails, full URLs, or raw error strings;
- alerts firing on internal noise or linking to stale runbooks;
- async consumers or edge hops dropping trace or correlation IDs;
- migrations, cutovers, or new services shipped without a verification or rollback runbook.

**The test:** if this fails at 3 AM, how fast does on-call know? Can telemetry isolate the cause, and does the runbook recover it?

## When it doesn't fit

- pure in-process libraries (expose typed errors and hooks for callers to instrument instead);
- throwaway prototypes (`play-with-me`).

**Showing it:** trigger a job failure, queue stall, or high-cardinality input and show silence, exploding series, or a broken runbook command.
