---
name: grill-with-docs
description: "Work through a plan or design one evidenced decision at a time while maintaining LESSON.md and AD_<N>.md. Use to specify a plan, architecture, or domain model."
---

# Grill with docs

Work through a plan or system design one evidenced decision at a time. Maintain durable terminology and findings in `~/.astack/<project>/lessons/<lesson>/LESSON.md` (**lookback**) and qualifying architecture decisions in `~/.astack/<project>/architecture/AD_<N>.md` (`$HOME/.astack` on POSIX, `%USERPROFILE%\.astack` on Windows, honoring `ASTACK_HOME`).

## 1. Work the design tree one decision at a time

Map the design as a dependency tree where each choice unlocks downstream branches. Pick the highest-impact open branch and send one exchange:

- **Decision:** what is being decided and what depends on it.
- **Evidence:** measurements, code paths, specs, or graded **research-this** findings.
- **Options and pick:** concrete alternatives side by side with latency, failure modes, and complexity. State your pick and why; propose alternatives when the current direction has flaws.

Wait for the answer. Never ask a load-bearing question without evidence—research missing facts first. Group only small independent questions; load-bearing decisions travel alone.

## 2. Show concrete scenarios, not adjectives

Use short sentences in the user's vocabulary and define technical terms inline. Replace bare adjectives ("simpler", "fragile", "scalable") with walked scenarios:

- **Option difference:** trace one request, fault, or load spike through each option to show where they diverge and what each costs.
- **Downside or benefit:** trace the exact failure triggered or prevented.
- **Conflict:** trace one scenario where two decisions collide.

## 3. Reconcile the cost ledger and domain terms on every answer

Keep a **cost ledger** beside settled decisions (latency, consistency, operational burden). On every answer:

- **Resolve conflicts first:** if the answer contradicts a settled decision or blows a shared budget when combined with prior costs, make that conflict the next exchange.
- **Add child branches:** record every new decision the answer implies (lifecycle, states, retries, monitoring, migration) as open branches.

Sharpen domain terms inline using existing `~/.astack/<project>/lessons/*/LESSON.md` memories (**lookup**):

- **Classify every domain term:** mark each domain noun or verb **canonical**, **retired**, or **open**.
- **Check code:** search the repo for existing names and synonyms; report mismatches with exact files and counts.
- **Test boundaries:** check each definition against concrete borderline cases and refine it if ambiguous.
- **Persist in `LESSON.md`:** record settled domain vocabulary, retired terms, and design lessons in `~/.astack/<project>/lessons/<lesson>/LESSON.md` (`astack-tools lessons path <project> <lesson> --ensure`, per **lookback**) rather than inside the repo.

## 4. Settle branches with checkable specs and `AD_<N>.md`

Choosing a direction does not settle a branch. Draft three concrete items for user approval:

1. **Implementation sketch:** small code or pseudocode in the project's stack.
2. **Test cases:** each naming the failure it catches and why it matters.
3. **Acceptance criteria:** checkable bounds, conditions, and invariants (never vague phrases like "works correctly").

Write `~/.astack/<project>/architecture/AD_<N>.md` (resolve and create cross-OS via `astack-tools arch path <project> --next --ensure`, per [AD-FORMAT.md](./AD-FORMAT.md)) only when a decision is hard to reverse, non-obvious without context, and resolves a real trade-off. Record settled specs, the cost ledger, rejected alternatives, acceptance criteria, tests, and evidence. Add dated `As built` updates once implemented.

## 5. Research with receipts and keep moving parts minimal

Dispatch read-only `astack-researcher` subagents (`research-this`, `rtfm`) on upcoming branches while waiting on answers. Weigh evidence in **prove-it** / **research-this** order: live measurements and repo code, then standards and papers, then external experience reports (each reflects one workload). Apply the same bar to user-supplied numbers; run **ab-test** or **benchmarking** when measurements settle a choice. State when evidence is thin.

Optimize correctness, then robustness, then efficiency, with minimal moving parts. Name concrete mechanisms (data structures, locks, messages) before inventing terms. Back both pushback and agreement with evidence. Reverse a pick only by naming the new fact that changed it. When the user overrules the evidence, record the overrule and their reasoning as theirs.

## 6. Pause and finish

If the session pauses with open branches, save the tree, accepted specs, cost ledger, open branches, and pending research under `~/.astack/<project>/architecture/GRILLING.md` so the next session resumes cleanly without dirtying the repo.

**Done when:** every branch has an accepted spec or explicit deferral, every load-bearing choice was tested against alternatives, domain terms and lessons are saved in `~/.astack/<project>/lessons/<lesson>/LESSON.md`, qualifying `~/.astack/<project>/architecture/AD_<N>.md` docs are written, and the user confirms the summary before implementation starts.

Referenced skills: `lookback` (`../lookback/SKILL.md`), `research-this` (`../research-this/SKILL.md`), `lookup` (`../lookup/SKILL.md`), `prove-it` (`../prove-it/SKILL.md`), `ab-test` (`../ab-test/SKILL.md`), `benchmarking` (`../benchmarking/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts grilling, grill-with-docs, and domain-modeling from mattpocock/skills and adalundhe/mp-skills (MIT, Copyright (c) 2026 Matt Pocock). See NOTICE.md. -->
