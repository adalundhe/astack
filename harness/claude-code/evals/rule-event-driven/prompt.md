---
description: "In Go mode, refactoring a sleep-polling background job waiter in ./repo routes to event-driven, replaces time.sleep polling with threading.Event or concurrent.futures completion notifications, and adds deterministic tests without wall-clock sleeps."
expected_outcome: "Reads event-driven/SKILL.md, removes time.sleep polling in ./repo/src/job_runner.py in favor of threading.Event or concurrent.futures completion notification with bounded timeouts and immediate wakeup on completion or failure, and adds deterministic unit tests verifying zero time.sleep calls."
timeout_seconds: 360
---

`/astack:go` Refactor `JobRunner` in `./repo/src/job_runner.py` (see `./repo/README.md` for the contract). Right now `wait_for` and `wait_all` spin in a fixed `time.sleep(0.2)` polling loop, wasting hundreds of milliseconds on fast jobs, delaying exception propagation, and overshooting tight timeouts. Replace the sleep polling with direct completion notifications (`threading.Event` or `concurrent.futures`) so waiters wake immediately on completion or failure with bounded timeouts and zero `time.sleep` calls, and add deterministic unit tests in `./repo/tests/` without relying on wall-clock sleeps.
