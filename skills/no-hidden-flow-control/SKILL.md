---
name: no-hidden-flow-control
description: "Handle specific failures narrowly or return typed errors; avoid catch-alls and exception control flow. Use when writing or reviewing error handling."
disable-model-invocation: true
---

# No hidden flow control

Handle each failure specifically where it happens, or return it as a typed value.

## Start with

1. **Return expected failures as typed values**. Put expected outcomes—not found, invalid input, conflict, timeout—in return types. Use idiomatic types: Rust `Result`, Go `errors.Is`/`errors.As`, TypeScript unions, or Python union `match`.
2. **Narrow exception handlers**. Catch only the exact exception right around the raising call, then handle or convert it. Let everything else propagate, because broad catches hide real bugs.
3. **Never swallow failures silently,** because hidden errors corrupt downstream state. If continuing after an error is intentional, reflect it in the returned value.
4. **Keep control flow visible at the call site**. Never break loops with exceptions, mutate state in catch blocks, or overwrite returns in `finally`. Make retries explicit and preserve the last failure (**fail-safely**).
5. **Let cancellation, interrupts, and programmer bugs propagate,** because catching them stalls shutdown and masks defects.
6. **Test every failure path:** trigger each error value and verify how callers handle it.

## Watch for

- broad catch-alls (`except:`, `except Exception`, `catch (e)`, `catch (Throwable)`, `.catch()` on a chain, Go `recover`);
- swallowed errors: empty catch blocks, log-and-continue, `null`/`false` defaults on failure, or ignored errors (`_ = err`, `.ok()`);
- exceptions thrown to signal normal outcomes or exit loops and caught far away;
- catch blocks steering execution or mutating flags, retry wrappers hiding errors, or `finally` blocks altering results;
- blanket middleware or decorators collapsing distinct failures into one generic error;
- hidden callbacks, signals, or hooks altering execution flow invisibly from the call site.

**The test:** from the call site alone, can you see every failure mode and what happens next?

## When it doesn't fit

- a single top-level boundary handler (HTTP entry, CLI `main`, worker loop) that logs context and returns a proper error;
- intentional partial-success flows (e.g. best-effort cleanup) whose return value reports what failed;
- exceptions required by a framework's own protocol, raised and caught strictly where expected.

**Showing it:** trigger an unexpected error the handler actually catches (e.g., `KeyError`/`TypeError` under Python `except Exception`, or cancellation/`KeyboardInterrupt` under bare `except:` or `catch (Throwable)`) and show how it gets swallowed.

<!-- Adapts pstack's boundary-discipline principle (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
