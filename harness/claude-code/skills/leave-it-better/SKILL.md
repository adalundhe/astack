---
name: leave-it-better
description: "Fix the broken things you run into (failing tests, broken CI or builds, failed security or dependency checks) at their cause, in a separate PR, instead of working around them. Use whenever something you didn't break gets in your way."
---

# Leave it better

Fix the broken tests, builds and checks you run into, in a separate PR, even when you didn't break them.

1. **Check it isn't yours.** Reproduce it on the base branch without your changes. If your changes caused it, fix it as part of your own work.
2. **Fix the cause, not the symptom** (**bugs-by-scenario**). A flaky test is a bug in the test or the code; find out which. Rerunning until it passes isn't a fix.
3. **Fix it separately:** its own branch from the base and its own PR, starting from a failing test. Keep it out of your own PR so each can be reviewed and reverted alone, and link the two.
4. **Never silence a check.** Don't skip, disable, quarantine or loosen a test, scan or rule to get past it. If the check itself is wrong, fix the check, and show why it was wrong.
5. **Keep your own work going** while the fix is reviewed, and rebase onto it when it merges.
6. **Report it:** what was broken, why, and the PR that fixes it.
