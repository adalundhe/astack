---
name: event-driven
description: "Wake work on the event that unblocks it instead of timers, sleeps, or polling loops. Use when writing or reviewing waiting, retry, refresh, or polling code, or agent wait loops."
disable-model-invocation: true
---

# Event-driven, not timers

Trigger work from the event that unblocks it rather than a timer, sleep, or polling loop.

## Start with

1. **Wait directly on the unblocking event:** a channel, condition variable, future/promise, notification, file watcher, or webhook.
2. **Add an event if none exists:** have the producer emit one rather than polling it.
3. **Derive or adapt timeouts and deadlines** instead of hardcoding them (**no-picked-constants**).
4. **Keep event ordering replayable:** identical inputs and seeds should produce identical event order.
5. **Apply this to agent workflows too:** wait for completion notifications from runs or workers instead of polling by hand (**automate-this**).

## Watch for

- `sleep`, fixed delays, or tickers on paths waiting for another task;
- polling loops (`check -> sleep -> check`);
- fixed-backoff retry loops waiting for a resource to appear;
- scheduled refresh timers where change notifications exist;
- agents manually re-checking CI, builds, or other agents.

**The test:** what event is this actually waiting for, and why isn't it waking on that event?

## When it doesn't fit

- inherently time-based work: deadlines, timeouts, heartbeats, and explicit schedules (e.g. a nightly job);
- retries after failure paced by the server's signal (e.g. `Retry-After`);
- polling an external system you don't control that exposes no event mechanism, at its documented rate (noted in code).

**Showing it:** measure added latency or wasted idle work from the timer, or demonstrate a state change missed between polls using a controlled clock.
