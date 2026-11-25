---
name: leave-it-better
description: "Fix unrelated broken tests, builds, CI, or security/dependency checks at their root cause in a separate PR instead of working around them. Use when preexisting breakage blocks your work."
disable-model-invocation: true
---

# Leave it better

Fix broken tests, builds, and checks you run into at their root cause in a separate PR, even if you didn't break them.

1. **Confirm it's preexisting.** Reproduce the failure on the base branch without your changes. If your changes caused it, fix it inside your own work.
2. **Fix the root cause, not the symptom** (**find-it**, **fix-it**). Treat flaky tests as real bugs in either the test or product code—don't just rerun until green.
3. **Isolate the fix.** Branch from the base branch, start with a failing test, and open a separate PR so it can be reviewed and reverted independently. Cross-link the two PRs.
4. **Never silence a check.** Don't skip, disable, quarantine, or weaken tests, scans, or lint rules to get past them. If a check itself is wrong, fix it and explain why.
5. **Don't stall your main task:** keep working while the fix PR is reviewed, then rebase onto it once merged.
6. **Report it:** state what was broken, why, and the link to the fix PR.

Referenced skills: `find-it` (`${CLAUDE_SKILL_DIR}/../find-it/SKILL.md`), `fix-it` (`${CLAUDE_SKILL_DIR}/../fix-it/SKILL.md`). Read any cited skill file before acting when its trigger applies.
