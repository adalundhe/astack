---
name: no-hidden-flow-control
description: "Handle each failure specifically where it happens, or return it as a typed value; no broad try/except or try/catch, swallowed errors, or exceptions as control flow. Use when writing or reviewing error handling."
---

# No hidden flow control

Handle each failure specifically where it happens, or return it to the caller as a typed value.

## Start with

1. **Return errors as typed values** the caller must handle, by the language's own means: Rust's `Result` with an error enum; Go's returned errors, checked with `errors.Is` and `errors.As`; a discriminated union in TypeScript; a union of result and error types, matched with `match`, in Python. Expected failures (not found, invalid input, conflict, timeout) usually work best as values.
2. **Where exceptions remain,** because the language or a library throws them, catch the specific type around the one call that raises it, and handle it there or turn it into a typed value. Let everything else propagate.
3. **Don't swallow a failure.** If carrying on is right, make the result say so.
4. **Keep control visible at the call site:** no exceptions to leave loops, no handlers changing state on the side, no `finally` changing the result. Retries are explicit and report their last failure (**event-driven**).
5. **Let cancellation, interrupts and programming errors propagate.**
6. **Test each failure path:** a test produces each error value and checks how its caller handles it.

## Watch for

- broad handlers: a bare `except:` or `except Exception`, `catch (e)` or `catch (Throwable t)` around a large block, a `.catch` on a whole chain, Go's `recover`;
- swallowed errors: empty handlers; log and carry on; a default, null, empty list or `false` returned for a failure; an ignored error (`_ = err`, Rust's `.ok()` or `.unwrap_or_default()` where the error matters);
- exceptions thrown to leave a loop or to signal an expected outcome, and caught far away;
- handlers that steer: catch blocks that set flags or change state, retry wrappers that hide each failure, a `finally` that changes the result;
- one handler for everything: a decorator, middleware or wrapper that turns every failure into one generic outcome;
- callbacks, signals or events that decide what runs next, invisible at the call site.

**The test:** from the call site alone, can you see every way this can fail, and what happens next?

## When it doesn't fit

- one top-level handler at the program's outer edge (a request handler, a CLI's entry point, a job loop) that reports the failure (logs it with context, returns an error, exits non-zero) and never hides it;
- carrying on after a failure when that's the designed behaviour and the returned value says so, such as best-effort cleanup that reports what it couldn't do;
- exceptions a framework uses as its own protocol, raised and handled where the framework expects them;
- an approach the evidence here favours: when unsure, try both and measure (**ab-test**), and say why you chose it.

**Showing it:** raise, inside the handler, an error it shouldn't catch (a typo'd name, a cancellation) and show what users get.

<!-- Adapts pstack's boundary-discipline principle (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
