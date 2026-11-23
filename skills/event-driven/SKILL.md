---
name: event-driven
description: "Wake work on the event that unblocks it, never on a timer, sleep or polling loop. Use when writing or reviewing code that waits, retries, refreshes or loops, or when a tick, poll or sleep sits on a hot path."
---

# Event-driven, not timers

Each step wakes on its event: an arrival, a completion, readiness, a reply. Time is used only for what is about time: deadlines, timeouts, heartbeats.

**Why:** a timer adds latency up to its interval and burns work while idle. A poll misses changes between looks and falls behind under load.

- If there is no event to wake on, make the producer send one.
- Remove a timer from a hot path. Shortening it only trades latency for waste.
- Learn deadline lengths; don't pick them (**no-picked-constants**).
- For a given input and seed, events happen in the same order, so any run can be replayed.
- The same goes for agents: wait for the notice that a run or a worker finished, not a polling loop.
