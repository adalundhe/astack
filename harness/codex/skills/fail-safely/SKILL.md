---
name: fail-safely
description: "Design and review networked, cloud, edge, and distributed components to survive partial failure without cascading outages: bounded timeouts/queues/pools, jittered backoff with retry budgets, decoupled health probes, graceful drain, origin shielding, and failure-domain resilience. Use when writing or reviewing network clients, queues, workloads, retries, pools, CDNs/edge, or distributed services."
---

# Fail safely

Assume any downstream, network hop, host, or failure domain can slow down, drop packets, restart, or vanish—design every boundary to degrade cleanly rather than amplifying a blip into a fleet-wide outage.

Apply these principles across whatever compute, orchestrator, serverless, edge/CDN, or messaging platform the system uses (**analyze-environment**).

## Start with

1. **Bound every wait, queue, pool, and fan-out (**no-picked-constants**):** set explicit connect, read, and total deadline timeouts on every network/DB call; cap connection pools, worker/serverless concurrency, edge subrequests, and in-memory queue depths with explicit backpressure or load shedding instead of unbounded growth.
2. **Prevent retry storms and origin stampedes:** retry only idempotent/retryable operations (**safe-to-rerun**) using exponential backoff with full jitter, a strict retry budget or cap, and circuit breakers / bulkheads so one failing downstream cannot starve healthy routes. Behind CDNs/caches/edge layers, protect origins with cache shielding, request coalescing, stale-while-revalidate/stale-if-error, and rate limits.
3. **Decouple liveness from external dependencies:** local liveness checks verify only whether the process itself is deadlocked/wedged—never query external DBs or downstream services inside a liveness probe (a downstream blip will trigger simultaneous restarts across the entire fleet). Reserve readiness and load-balancer/origin health checks for serving readiness, and startup checks for slow boot.
4. **Drain gracefully on deploys and shutdown:** handle shutdown signals (`SIGTERM`), wait for load-balancer/service-mesh/endpoint deregistration to propagate before closing listeners, finish in-flight work within the grace budget, and close pools cleanly so rolling deploys don't emit 502s/503s.
5. **Survive host, zone, and origin loss:** distribute replicas across independent failure domains (zones/regions/origin pools), configure disruption budgets and explicit CPU/memory limits, and keep critical tiers stateless or cleanly replicated.
6. **Prove failure behavior under injected faults (**full-spectrum-testing**):** simulate slow/blackholed downstreams, mid-request shutdown, pool exhaustion, and partial dependency loss—never assume happy-path tests prove resilience.

## Watch for

- network or DB clients using default infinite timeouts or sharing one unbounded pool across critical and best-effort traffic;
- tight retries without jitter or retry budgets, or cache-busting / stampeding straight into an unprotected origin;
- liveness probes coupled to external DBs, caches, or upstream APIs;
- workloads exiting immediately on shutdown before load balancers/edge pools drain traffic (deploy-time 502 spikes);
- single-instance or single-failure-domain critical services lacking disruption budgets, zone spread, or origin failover;
- serverless/edge workloads hitting unbounded cold-start storms, compute/subrequest limits, or silent sync blocking.

**The test:** if one downstream stalls for 30s, or a host/zone/origin rolls or drops mid-traffic, does the system degrade cleanly and recover automatically without cascading failures?

## When it doesn't fit

- local single-process CLI tools or offline scripts with no network callers or live serving SLO;
- single-node local dev/test fixtures where multi-domain/disruption-budget rules aren't meaningful.

**Showing it:** inject latency, dependency failure, or graceful shutdown under concurrent load and show the timeout hang, retry/origin amplification, fleet restart loop, OOM, or dropped in-flight requests.

Referenced skills: `analyze-environment` (`../analyze-environment/SKILL.md`), `no-picked-constants` (`../no-picked-constants/SKILL.md`), `safe-to-rerun` (`../safe-to-rerun/SKILL.md`), `full-spectrum-testing` (`../full-spectrum-testing/SKILL.md`). Read any cited skill file before acting when its trigger applies.
