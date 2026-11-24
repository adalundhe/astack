---
name: address-feedback
description: "Close every review finding and PR comment, from people or agents: fix it, answer it, or show it's wrong, blockers first, replying on each. Use when a reviewer returns findings, or comments arrive on your PR."
---

# Address feedback

Fix, answer or refute every review finding and PR comment, and reply to each.

1. **Gather everything:** the reviewer's findings, or every comment and review on the PR, from people and agents alike.
2. **Work blockers first,** then suggestions, then nits. Nits count too.
3. **Try each one before you act.** Run its reproduction, or set up the case it describes.
   - **It's real:** fix it, starting from the reproduction as a failing test (**bugs-by-scenario**). A rule finding is fixed the way the rule's Start with section suggests, or answered with evidence that this context calls for something else (**worrywart**).
   - **It's a question:** answer it. If the code made someone ask, change the code so it doesn't: a better name or a test, not a comment.
   - **It's wrong:** show it with evidence (**worrywart**).
   - **Only the person can decide it,** such as a product call or giving up functionality: ask them directly, with your recommendation, and keep going on the rest.
4. **Reply on each thread:** what you changed and the commit, or your evidence, or your answer. Resolve a thread only after that, never silently.
5. **Send it back for review,** and repeat until it comes back clear.

If the work keeps coming back with new rounds of feedback, tell whoever assigned it (the lead, in Go mode) so they can add help.
