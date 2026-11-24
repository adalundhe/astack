---
name: watch-pr
description: "Take reviewed code through its PR: open it, monitor CI and comments via background watchers, fix failures, resolve every comment, ping if open 24h, hand off at time limit, and report when merge-ready. Use once review clears or when taking over a PR."
---

# Watch a PR

Shepherd a pull request to merge-ready state without merging it yourself.

Merge-ready means CI is green, every human and agent comment is resolved, and all required approvals are in.

1. **Open the PR** only after review clears: zero blockers, and every suggestion/nit fixed, answered, or refuted (**worrywart**). Write a clear description: problem, what changed, how it was tested, and how to verify it.
2. **Maintain a handoff marker.** In the program folder, keep `watch/<PR number>.md` updated on every event with PR URL, branch, head SHA, CI status, each comment's status, open timestamp, and next 24h ping time so a successor can pick up cold.
3. **Watch on events, not manual polling.** Run a background watcher that returns when CI finishes, a comment/review arrives, or the next reminder comes due (**automate-this**). Don't burn turns polling by hand.
4. **Rebase only when needed; carry verdicts cleanly.** Rebase onto the target branch only when target has moved in a way that would otherwise land untested code (or blocks merge with conflicts). After a rebase, carry your prior review/test verdict only when `git patch-id` of your commits is identical and the target's new commits do not overlap the PR's **blast-radius**; otherwise re-verify before declaring merge-ready.
5. **Fix CI failures.** If the failure is preexisting (broken `main`, failing scan, broken dependency, flaky check), fix its root cause in a separate PR (**leave-it-better**) while keeping this PR moving.
6. **Address feedback promptly** (**address-feedback**): fix, answer, or refute with evidence until every thread is resolved.
7. **Flag if stuck 24 hours:** every 24h the PR stays open, comment mentioning the person with what it's waiting on and log a line in `LANES.md`.
8. **Hand off cleanly at wind-down:** update the marker file, report exact PR status, and stop so a successor can continue seamlessly.
9. **Stop when merge-ready:** notify the lead (or the person, if running standalone) and stop. Never merge the PR yourself.

Referenced skills: `worrywart` (`../worrywart/SKILL.md`), `automate-this` (`../automate-this/SKILL.md`), `blast-radius` (`../blast-radius/SKILL.md`), `leave-it-better` (`../leave-it-better/SKILL.md`), `address-feedback` (`../address-feedback/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's autopilot-full rebase and verdict carry-over rules (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
