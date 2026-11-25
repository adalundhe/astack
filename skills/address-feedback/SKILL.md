---
name: address-feedback
description: "Resolve every review finding and PR comment from humans or agents by fixing, answering, or disproving it, blockers first, replying on every thread. Use when review findings or PR comments arrive."
disable-model-invocation: true
---

# Address feedback

Close every review finding and PR comment by fixing it, answering it, or disproving it, and reply on every thread.

1. **Collect everything:** all reviewer findings, or every comment and review on the PR from both humans and agents.
2. **Work blockers first,** then suggestions, then nits. Don't skip nits.
3. **Verify each item before acting.** Run its reproduction or set up the case it describes.
   - **Real issue:** turn the reproduction into a failing test, then fix the cause (**bugs-by-scenario**). For a coding-rule finding, either apply the rule's `Start with` guidance or show why this context warrants an exception (**worrywart**).
   - **Question:** answer it clearly. If confusing code caused the question, clarify the code with better naming or a test rather than adding an explanatory comment.
   - **Wrong or overstated:** refute it with evidence (**worrywart**).
   - **Needs a human call** (such as a product trade-off or dropping functionality): ask the person directly with your recommendation, and keep working on the rest.
4. **Diff-growth guard (**simplify-me**):** check the PR's diff size each review round (`astack-watch-pr diff-guard --base origin/<base> --head HEAD --json`). Review loops tend to grow a PR one cheap fix at a time: if review grew the diff, run **simplify-me** to cut, narrow, or delete before adding more code—prefer the fix that simplifies or deletes, and decline out-of-scope or non-bug requests with a clear written reason.
5. **Preserve takeover credit:** if finishing or amending commits authored by someone else, keep original git authorship (`git rebase`/`git cherry-pick`/`--author`) or include `Co-authored-by: Name <email>` trailers (verify with `astack-watch-pr authorship-check`).
6. **Reply on every thread plainly (**wat**, **leave-feedback**):** state the fix and context clearly, share concrete evidence, or give a direct answer with full context—never cryptic isolated fragments or unintroduced commit hashes. Before posting any human-facing PR reply, run **leave-feedback** so a second independent reviewer agent audits the draft until it returns `CLEAR`, then post via `astack-watch-pr reply --body-file <reply.md> --audit-receipt <audit_clear.txt>` (or the matching forge CLI `astack-watch-github` / `astack-watch-gitlab` / `astack-watch-bitbucket`). Only resolve a thread after replying—never silently.
7. **Run vectored review on code fixes (**review**) and re-request review:** whenever addressing feedback changed code or tests, run `astack-check-gates` and vectored **review** (`astack-review-ledger`) before pushing, then re-request review and repeat until it comes back clear.

If the same work keeps coming back with new rounds of feedback, escalate to whoever assigned it (or the lead, in an astack program) so they can adjust the plan or add help.
