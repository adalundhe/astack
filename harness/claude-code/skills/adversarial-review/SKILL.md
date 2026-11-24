---
name: adversarial-review
description: "Review a change by reproducing the original bug, confirming acceptance criteria, trying to break it in its real environment, checking coding rules, and reporting proven blockers first. Use when reviewing a fix, feature, branch, or PR."
---

# Adversarial review

Review a change by trying to break it the way its users would, in its real environment.

1. **Run it for real.** Use a local development environment whenever possible, or an environment the person explicitly approved. Never test against production or unapproved systems.
2. **Judge it in context.** Learn how the code runs in production and what surrounds it. Don't raise issues already handled by surrounding systems, upstream layers, or documented operational practices.
3. **Reproduce before the change.** Without the change, reproduce every bug it claims to fix from the user's side. If you can't reproduce a failure, report it as unreproduced rather than fixed.
4. **Verify the change.** With the change applied, rerun each reproduction and verify every acceptance criterion and test it claims. Report anything missing or partial.
5. **Attack it.** Stress-test the change from the user's side across every category that applies:
   - **Input:** invalid, empty, huge, malformed, oddly encoded, out of order.
   - **Load:** concurrent callers, bursts, sustained overload.
   - **Faults:** slow or failing dependencies, mid-operation restarts, lost or duplicated messages, full disk.
   - **Concurrency:** races, deadlocks, and livelocks wherever locks, retries, or waits exist.
   - **Misuse:** plausible mistakes by a confused user, scripted client, or another agent.

   Seed generated inputs and fault schedules as in **full-spectrum-testing**.
6. **Check rules and complexity.** For each applicable coding-rule skill, check its `Watch for` list and `When it doesn't fit` exceptions. Violating the person's explicit rules, or departing from a coding rule's defaults without justification, is a finding even when tests pass. Note where a simpler implementation meets the same bar (**simplify-me**).
7. **Prove every finding.** Include a runnable reproduction: steps or command, actual output, and expected output. Blockers must be proven locally; unproven suspicions go under unproven and never block. Run each reproduction without the change too, and state whether the change caused it, left it in place, or failed to fix it. For a rule violation, prove it using the rule's `Showing it` check or cite the exact file and line.
8. **Rank internally by user impact:**
   - **P0:** critical outage or multiple/whole systems broken.
   - **P1:** widespread breakage or severe degradation across common features or a core system.
   - **P2:** primary feature broken, or inconsistent/limited widespread breakage.
   - **P3:** isolated secondary feature broken, notable single-feature degradation, or notable non-breaking bug in a primary feature.
   - **P4:** isolated intermittent issue, moderate degradation, or minor non-breaking bug in a secondary feature.
   - **P5:** rare, non-breaking nit.

   P0–P2 are blocking, P3 is a suggestion, P4 is a suggestion or nit, and P5 is a nit. Keep the P0–P5 labels internal; don't print them in the report.
9. **Report clearly.** Lead with blockers, then suggestions, then nits. Start each finding with user impact (what breaks and when), then the reproduction, brief evidence, and concrete fix (what to change and where; for a rule departure, cite the rule's `Start with` guidance or the evidence needed to justify keeping it). Finish with what you tested that held. Don't edit the code under review; save reproductions as standalone files the fix can adopt as failing tests.
