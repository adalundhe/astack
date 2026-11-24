---
name: no-hidden-flow-control
description: "Handle specific failures where they happen or return typed error values; avoid broad catch-alls, swallowed errors, or exceptions used as control flow. Use when writing or reviewing error handling."
---

# No hidden flow control

Handle each failure specifically where it happens, or return it to the caller as a typed value.

## Start with

1. **Return expected failures as typed values** using the language's idioms (Rust `Result` + error enum, Go returned errors checked with `errors.Is`/`errors.As`, TypeScript discriminated unions, Python union types matched with `match`). Expected outcomes—not found, invalid input, conflict, timeout—belong in return types.
2. **Narrow any exception handlers.** When a language or library throws, catch only the exact exception type right around the call that raises it, then handle it or convert it into a typed error. Let everything else propagate.
3. **Never swallow failures silently.** If continuing after an error is intentional, reflect it in the returned value.
4. **Keep control flow visible at the call site:** don't use exceptions to break out of loops, don't mutate state inside catch blocks, and don't overwrite return values in `finally`. Make retries explicit and preserve the last failure (**event-driven**).
5. **Let cancellation, interrupts, and programmer bugs propagate.**
6. **Test every failure path:** trigger each error value and verify how callers handle it.

## Watch for

- broad catch-alls (`except:`, `except Exception`, `catch (e)`, `catch (Throwable)`, `.catch()` wrapping a whole chain, Go `recover`);
- swallowed errors: empty catch blocks, log-and-continue, returning `null`/`false`/empty defaults on failure, ignored errors (`_ = err`, `.ok()`, `.unwrap_or_default()` where the error matters);
- exceptions thrown to signal normal outcomes or exit loops and caught far away;
- catch blocks that silently steer execution or mutate flags, retry wrappers hiding intermediate errors, or `finally` blocks altering results;
- blanket middleware/decorators collapsing distinct failures into one generic error;
- hidden callbacks, signals, or hooks altering execution flow invisibly from the call site.

**The test:** from the call site alone, can you see every way this call can fail and what happens next?

## When it doesn't fit

- a single top-level boundary handler (HTTP entry point, CLI `main`, job worker loop) that logs context, returns a proper error response or non-zero exit code, and never hides failures;
- intentional partial-success flows (e.g. best-effort cleanup) whose return value explicitly reports what failed;
- exceptions required by a framework's own protocol, raised and caught strictly where the framework expects them;
- an alternative backed by measurements (**ab-test**), with the trade-off documented.

**Showing it:** trigger an unexpected error (e.g. a typo/NameError or cancellation) inside the handler and show how it gets swallowed or mishandled.

Referenced skills: `event-driven` (`../event-driven/SKILL.md`), `ab-test` (`../ab-test/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's boundary-discipline principle (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
