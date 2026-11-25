---
name: address-feedback
description: "Resolve every review finding and PR comment from humans or agents by fixing, answering, or disproving it, blockers first, replying on every thread. Use when review findings or PR comments arrive."
disable-model-invocation: true
---

# Address feedback

Close every review finding and PR comment by fixing, answering, or disproving it, and reply on every thread.

1. **Collect everything:** gather all reviewer findings and every human or bot PR comment.
2. **Work blockers first,** then suggestions, then nits. Don't skip nits.
3. **Verify each item before acting.** Run its reproduction or test the described case:
   - **Real issue:** turn the repro into a failing test, then fix the root cause (**find-it**, **fix-it**). For coding-rule findings, follow `Start with` or justify the exception (**worrywart**).
   - **Question:** answer clearly. If confusing code caused it, improve the naming or test rather than adding a narrating comment.
   - **Wrong or overstated:** refute it with runnable evidence (**worrywart**).
   - **Needs a human call:** escalate with your recommendation and keep working on the rest.
4. **Guard against diff bloat (**simplify-me**):** run `astack-watch-pr diff-guard` each review round. Review loops tend to pile on cheap fixes: if the diff grew, cut or simplify before adding code, and decline out-of-scope requests with a written reason.
5. **Preserve takeover credit:** when amending another contributor's commits, keep original authorship (`--author`) or `Co-authored-by` trailers and verify with `astack-watch-pr authorship-check`.
6. **Reply on every thread plainly (**wat**, **leave-feedback**):** state the fix, evidence, or answer with full context—never bare commit hashes or cryptic fragments. Before posting any human-facing PR reply, the **lead** audits the draft with an independent second reviewer via **leave-feedback** until `CLEAR`, then posts via `astack-watch-pr reply`. Resolve threads only after replying. (Workers draft replies in their report and never spawn reviewers.)
7. **Re-review code fixes (**review**):** if addressing feedback changed code or tests, the **lead** runs `astack-check-gates` and vectored **review** (`astack-review-ledger`) before pushing, routes any new findings to a fresh worker, then re-requests review.

If the same work keeps bouncing across rounds, escalate to the lead so they can adjust the plan or add help.

Referenced skills: `find-it` (`../find-it/SKILL.md`), `fix-it` (`../fix-it/SKILL.md`), `worrywart` (`../worrywart/SKILL.md`), `simplify-me` (`../simplify-me/SKILL.md`), `wat` (`../wat/SKILL.md`), `leave-feedback` (`../leave-feedback/SKILL.md`), `lead` (`../astack-lead/SKILL.md`), `review` (`../astack-review/SKILL.md`). Read any cited skill file before acting when its trigger applies.
