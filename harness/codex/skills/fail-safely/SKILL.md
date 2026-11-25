---
name: fail-safely
description: "Design networked and distributed boundaries to survive partial failure without cascading outages. Use when building or reviewing network clients, services, probes, or deploys."
---

# Fail safely

Assume any downstream, network hop, host, or failure domain can slow down, restart, or vanish. Design every boundary to degrade cleanly instead of turning a blip into a fleet outage.

Apply this across whatever compute, orchestrator, serverless, edge/CDN, or messaging platform the system runs on (`analyze-environment`).

## Start with

1. **Bound every wait, queue, pool, and fan-out (`no-picked-constants`):** set explicit connect, read, and total deadlines on every network and DB call. Cap pools, concurrency, subrequests, and queues with backpressure, because unbounded queues exhaust memory and wedge callers.
2. **Prevent retry storms and origin stampedes:** retry only idempotent calls (**safe-to-rerun**) with exponential backoff, full jitter, and a retry budget. Add circuit breakers or bulkheads, because synchronized retries amplify partial outages into fleet storms. Behind CDNs and caches, protect origins with shielding, coalescing, stale-if-error, and rate limits.
3. **Decouple liveness from external dependencies:** liveness probes check only whether the process itself is wedged. Never query external DBs or APIs in liveness probes, because a downstream blip will restart the entire fleet. Use readiness checks for traffic and startup checks for slow boot.
4. **Drain gracefully on deploys and shutdown:** handle `SIGTERM` and wait for load-balancer deregistration before closing listeners. Finish in-flight requests within grace time, then close pools cleanly so deploys never spike 502s/503s.
5. **Survive host, zone, and origin loss:** spread replicas across independent failure domains and set disruption budgets. Enforce explicit CPU/memory limits, and keep critical tiers stateless or cleanly replicated.
6. **Prove resilience under injected faults (`full-spectrum-testing`):** simulate slow or blackholed downstreams, mid-request shutdown, pool exhaustion, and dependency loss. Happy-path tests never prove resilience.

## Watch for

- network or DB clients with infinite default timeouts or one unbounded shared pool;
- tight retries lacking jitter or budgets, or cache-busting straight into an unprotected origin;
- liveness probes coupled to external DBs, caches, or upstream APIs;
- workloads exiting on `SIGTERM` before load balancers drain traffic;
- single-zone critical services lacking disruption budgets or origin failover;
- serverless or edge handlers hitting cold-start storms or subrequest caps.

**The test:** if one downstream stalls for 30s, or a host or zone drops mid-traffic, does the system degrade cleanly?

## When it doesn't fit

- local single-process CLIs or offline scripts with no network callers or live serving SLO;
- single-node local dev fixtures where multi-domain disruption budgets don't apply.

**Showing it:** inject latency, dependency failure, or shutdown under concurrent load. Show the hang, retry storm, restart loop, OOM, or dropped requests.

Referenced skills: `safe-to-rerun` (`../safe-to-rerun/SKILL.md`). Read any cited skill file before acting when its trigger applies.
