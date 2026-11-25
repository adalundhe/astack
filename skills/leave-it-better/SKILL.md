---
name: leave-it-better
description: "Fix preexisting broken tests, builds, CI, or security checks at root cause instead of working around them. Use when preexisting breakage blocks your work."
disable-model-invocation: true
---

# Leave it better

Apply only when preexisting breakage blocks your work; otherwise log one side-finding line and move on. Fix blocking breakage at its root cause instead of working around it.

1. **Confirm it's preexisting.** Reproduce the failure on the base branch without your changes. If your changes caused it, fix it inside your own work.
2. **Fix the root cause, not the symptom** (**find-it**, **fix-it**). Treat flaky tests as real bugs—never rerun until green.
3. **Isolate the fix.** Open a separate branch and PR from base when allowed, starting with a failing test and cross-linking PRs. Inside a worker lane, put it in its own commit noting ownership, or let the lead dispatch a lane.
4. **Never silence a check,** because silenced checks let regressions accumulate unseen. Never skip, disable, quarantine, or weaken tests, scans, or lints. If a gate or check itself is wrong, stop and report it with evidence; inside a lead program, change a gate only after the lead countersigns it in `RULES.md` `## Revisions`.
5. **Don't stall your main task:** keep working while the fix lands, then rebase onto it once merged.
6. **Report it:** state what was broken, why, and the fix commit or PR link.

**Done when:** the preexisting blocker is reproduced on base, fixed at root cause in an isolated commit or PR, and reported with no silenced checks.
