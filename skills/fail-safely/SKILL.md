---
name: fail-safely
description: "Design and review networked, cloud, edge, and distributed components to survive partial failure without cascading outages: bounded timeouts/queues/pools, jittered backoff with retry budgets, decoupled health probes, graceful drain, origin shielding, and failure-domain spread."
disable-model-invocation: true
---

# Fail safely

Assume any downstream, network hop, host, or failure domain can slow down, restart, or vanish. Design every boundary to degrade cleanly instead of amplifying a blip into a fleet outage.

Apply this across whatever compute, orchestrator, serverless, edge/CDN, or messaging platform the system runs on (**analyze-environment**).

## Start with

1. **Bound every wait, queue, pool, and fan-out (**no-picked-constants**):** set explicit connect, read, and total deadlines on every network and DB call. Cap connection pools, worker concurrency, edge subrequests, and queue depths with backpressure or load shedding instead of unbounded growth.
2. **Prevent retry storms and origin stampedes:** retry only idempotent operations (**safe-to-rerun**) with exponential backoff, full jitter, a retry budget, and circuit breakers or bulkheads. Behind CDNs and caches, protect origins with shielding, request coalescing, stale-while-revalidate/stale-if-error, and rate limits.
3. **Decouple liveness from external dependencies:** liveness checks verify only whether the process itself is wedged. Never query external DBs or upstream APIs inside liveness probes, because a downstream blip will restart the entire fleet at once. Use readiness checks for serving readiness and startup checks for slow boot.
4. **Drain gracefully on deploys and shutdown:** handle `SIGTERM`, wait for load-balancer deregistration to propagate before closing listeners, finish in-flight requests within grace time, and close pools cleanly so deploys don't spike 502s/503s.
5. **Survive host, zone, and origin loss:** spread replicas across independent failure domains, set disruption budgets and explicit CPU/memory limits, and keep critical tiers stateless or cleanly replicated.
6. **Prove resilience under injected faults (**full-spectrum-testing**):** simulate slow or blackholed downstreams, mid-request shutdown, pool exhaustion, and partial dependency loss. Happy-path tests never prove resilience.

## Watch for

- network or DB clients with infinite default timeouts or one unbounded shared pool;
- tight retries lacking jitter or budgets, or cache-busting straight into an unprotected origin;
- liveness probes coupled to external DBs, caches, or upstream APIs;
- workloads exiting on `SIGTERM` before load balancers drain traffic;
- single-zone critical services lacking disruption budgets or origin failover;
- serverless or edge handlers hitting cold-start storms or subrequest caps.

**The test:** if one downstream stalls for 30s, or a host, zone, or origin drops mid-traffic, does the system degrade cleanly and recover automatically?

## When it doesn't fit

- local single-process CLIs or offline scripts with no network callers or live serving SLO;
- single-node local dev fixtures where multi-domain disruption budgets don't apply.

**Showing it:** inject latency, dependency failure, or shutdown under concurrent load and show the hang, retry storm, fleet restart loop, OOM, or dropped requests.
