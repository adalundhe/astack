---
name: adversarial-review
description: "Review a change by trying to break it the way its users would, in its real setting: reproduce the reported failure without the change, confirm the change and its acceptance criteria, attack it, check it for slop and for a simpler way, and return proven findings as blocking, suggestions or nits. Use when reviewing a fix, a feature, a task's work before its PR, or a pull request."
---

# Adversarial review

Review a change by trying to break it the way its users would, in its real setting.

1. **Run it for real.** Use a local development environment wherever possible, otherwise only a development or remote environment the person has approved. Never anything else.
2. **Judge it in its setting.** Learn how it is used in production and what surrounds it. If other systems, software or clearly documented practices already handle an issue, it isn't raised. Period.
3. **Reproduce first.** Without the change, reproduce every failure it claims to fix, from the user's side. A failure you can't reproduce is reported as unreproduced, never as fixed.
4. **Then confirm it.** With the change, rerun each reproduction, and check every acceptance criterion and test it claims. Anything missing or partial is a finding.
5. **Then break it.** Attack it from its users' side, by every method that applies:
   - input: invalid, empty, huge, malformed, oddly encoded, out of order;
   - load: many callers at once, bursts, sustained overload;
   - faults: dependencies failing or slow, restarts mid-operation, lost or duplicated messages, a full disk;
   - concurrency: races, and deadlock and livelock wherever locks, retries or waits exist;
   - misuse: what a confused person, a scripted client or another agent would plausibly do.

   Generate inputs and fault schedules from a seed, as in **full-spectrum-testing**.
6. **Check it against the rules.** For each rule skill that applies, look for what its Watch for lists, and read its When it doesn't fit. Breaking the person's rules and preferences is slop. Departing from one of our rules' starting points is fine when the change shows why it fits this context better; with no reason given, it's slop. Slop is a finding even when nothing fails. Where a simpler implementation would meet the same bar, say so (**simplify-me**).
7. **Prove each finding.** A finding needs a reproduction its user could run: the steps or command, what happened, and what should have happened. A blocker must be proven by local testing; an issue you can't prove is noted as unproven and never blocks. Run each reproduction without the change too, and say whether the change caused it, left it in place, or failed to fix it. For a rule break, show it the way the rule's Showing it says, or cite the code by file and line.
8. **Rank it, privately, by its effect on users:**
   - **P0:** critical or blocking, or several systems or the whole system broken.
   - **P1:** widespread breakage or severe degradation: a set of common features, or one or more systems, broken or badly degraded.
   - **P2:** targeted breakage or degradation: a primary feature not working, or limited widespread degradation or inconsistent breakage.
   - **P3:** an isolated secondary feature broken, notable degradation of a single feature, or a notable non-breaking bug in a primary feature.
   - **P4:** isolated, intermittent breakage, moderate or inconsistent degradation, or a notable non-breaking bug in a secondary feature.
   - **P5:** non-breaking, rare degradation.

   P0 to P2 block. P3 is a suggestion. P4 is a recommendation or a nit, and P5 a nit. The scale orders your work; never show it.
9. **Report** blockers first, then suggestions, then nits. Write each impact first, in plain words: what the user sees and when. Then give the reproduction and the evidence, briefly, and the fix: what to change, and where; for a departure from a rule, its Start with section, or the evidence that would justify the departure. Then list what you tried that held. Change nothing in the code under review: leave each reproduction as a file a fix can adopt as its first failing test.
