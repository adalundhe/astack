---
name: event-driven
description: "Wake work on the event that unblocks it (an arrival, a completion, readiness, a reply), never on a timer, sleep or polling loop. Use when you write or review code that waits, retries, refreshes or drives a loop, or when you see a tick, poll, sleep or interval on a hot path."
---

# Event-driven, not timers

Each step wakes on its event: an arrival, readiness, a completion or a reply. Only what is truly about time uses time: a deadline, a timeout, an election, a heartbeat.

Ada's words: "We prefer clean, concise, deterministic, and event driven."

**Why:** a timer between an event and the work it unblocks adds latency up to its interval, burns cycles while idle, and makes behaviour depend on timing. A poll misses transitions that happen between looks, and falls behind under load.

- **Find the event** the wait is for, and wake on it: a channel, a condition, a completion queue, a notification, a callback. If no event exists, make the producer send one. **Why:** the producer knows when the state changed. A poller only guesses.
- **Remove a timer on a hot path. Don't shorten it.** **Why:** a shorter interval trades latency for wasted wakeups, and is still a picked number.
- **Real deadlines stay**, and their durations are learned (**no-picked-constants**). **Why:** a deadline is about time itself, so time is the right trigger.
- **Keep it deterministic.** The same inputs and seed give the same order of events. **Why:** a run you can replay is a bug you can fix.
- **The same holds for agents.** Wait on the notification that a run or a worker finished. Keep a long heartbeat only as the fallback for what sends no event. **Why:** re-checking in a loop burns tokens and still sees the change late.

You skipped this when code sleeps or polls for a condition another part of the system could signal, or when latency was fixed by shortening an interval.
