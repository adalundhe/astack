---
name: event-driven
description: "Wake work on the event that unblocks it, never on a timer, sleep or polling loop. Use when writing or reviewing code that waits, retries, refreshes or loops, or when a tick, poll or sleep sits on a hot path."
---

# Event-driven, not timers

Wake work on the event that unblocks it, not on a timer or a poll.

## Start with

1. **Wait on the event that unblocks the work:** a channel, a condition, a future, a notification, a file watch, a webhook.
2. **If there's no event to wake on,** make the producer send one.
3. **Learn deadlines and timeouts;** don't pick them (**no-picked-constants**).
4. **Keep it replayable:** for a given input and seed, events happen in the same order.
5. **Agents too** wait for the notice that a run or a worker finished, rather than polling (**automate-this**).

## Watch for

- sleeps, fixed delays and tickers on paths that wait for something else;
- polling loops: check, sleep, check again;
- retry loops with a fixed backoff, waiting for something to appear;
- timers that refresh state on a schedule instead of on change;
- agents re-checking CI, a run or another agent by hand.

**The test:** what event is this waiting for, and why isn't it waking on that event?

## When it doesn't fit

- time that is the point: deadlines, timeouts, heartbeats, and schedules the person set, such as a nightly job;
- a retry after a failure, timed by what the other side says, such as its `Retry-After`;
- polling a system you can't change that offers no event, at the rate it documents, said in the code.

**Showing it:** measure the latency the timer adds or the work it does while idle, or show a change the poll misses, with a controlled clock.
