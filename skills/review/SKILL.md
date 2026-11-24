---
name: review
description: "Review a change, a pull request or a whole program's work with a swarm of reviewers who try to break it as its users would; keep only findings a rerun proves, merge those with one cause, and report blockers first. Use before work moves on, and when asked to review, stress-test or tear apart a change."
---

# Review

Send reviewers to break the work, and keep only the findings a rerun proves.

1. **Set the scope:** what the person names; otherwise the current branch's changes since it left its base, uncommitted work included.
2. **State the intent** (**play-it-back**): what the change must do for its users, from the request, the briefs and acceptance criteria, the commits and the PR description.
3. **Send reviewers:** one reviewer agent per independent change, and for a single change one per lens that applies, each seeing the whole change:
   - its users' paths;
   - failure, load and concurrency;
   - the rules, run as checks: **no-implicit-states**, **no-hidden-flow-control**, **no-hidden-config**, **minimize-state-stores**, **check-your-boundaries**, **no-shared-writes**, **safe-to-rerun**, **no-bolt-ons**, **yagni**, **comment-cop**, **delight-users**.

   Each works in its own worktree with the uncommitted changes copied in, follows **adversarial-review** in full, and returns its report.
4. **Rerun every finding.** Keep one when its reproduction shows the failure and the failure breaks the intent. Drop the rest, counting each reviewer's drops and why.
5. **Merge findings with one cause,** naming every reviewer who found it. Keep every verified finding from every reviewer: they find different failures.
6. **Rank them privately** (**adversarial-review**) and report blockers first, then suggestions, then nits, each impact first with its reproduction and evidence. Then what was confirmed, what held, what couldn't be tested, and what was dropped.

Review changes nothing in the work under review. Findings go back to whoever made the change; in Go mode, the lead turns them into tasks.

<!-- Adapts pstack's interrogate skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
