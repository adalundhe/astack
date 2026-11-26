---
name: plan-it
description: "Interrogate and narrow an idea or system design one evidenced decision at a time before coding. Use when shaping a new idea, plan, or architecture."
disable-model-invocation: true
---

# Plan it

Shape an unshaped idea, feature, or system design before writing code. Interrogate the problem one evidenced decision at a time until every branch settles into a concrete spec. Delegate qualifying architecture decision documents to **create-adc** and execution graphs to **dagify** or **treeify**.

## Map the design tree and work one decision at a time

Represent the problem as a dependency tree where each choice unlocks downstream branches. Pick the highest-impact open branch first and send one focused exchange. State what is being decided and why it matters now. Attach your receipts: measurements, code paths, specs, or graded **research-this** findings. Compare credible options side by side by practical impact—latency, failure modes, and complexity—and state your pick.

Wait for the answer before moving on. Never ask a load-bearing question without evidence; research missing facts first. Keep load-bearing decisions one per exchange so nothing gets rubber-stamped in bulk. Group only small, independent choices.

## Demonstrate trade-offs with concrete scenarios

Write short, plain sentences in the user's vocabulary. Define technical terms inline where they first appear. Replace bare adjectives like "simpler", "fragile", or "scalable" with walked scenarios. Trace one concrete request, fault, or load spike through competing options to show where they split and what each costs. Play out the exact failure a downside causes, the failure a benefit prevents, or the point where two choices collide.

## Reconcile the cost ledger and domain terms on every answer

Keep a running cost ledger beside settled decisions tracking latency, consistency trade-offs, and operational burden. Check every new answer against the ledger right away. If it contradicts a prior decision or pushes combined costs past a shared budget, resolve that conflict on the next exchange. Expand the tree forward at the same time by entering every child branch the decision implies: lifecycle, states, retries, monitoring, and migration.

Sharpen domain language inline rather than waiting until the end. Check `~/.astack/<project>/lessons/*/LESSON.md` (**lookup**) and sweep the repo for existing terms and synonyms. Report any mismatch between spoken terms and code with exact files and counts. Test definitions against concrete borderline cases, and classify every domain term as canonical, retired, or open. Save settled terminology and design lessons to `~/.astack/<project>/lessons/<lesson>/LESSON.md` (**lookback**), never inside the repo.

## Settle branches with specs and hand ADs to `create-adc`

Choosing a direction opens a spec rather than settling the branch. Draft a small implementation sketch in the project's stack. Pair it with concrete test cases naming the failures they catch and checkable acceptance criteria—exact bounds, behaviors under named conditions, and invariants. A branch settles only when the user accepts its spec; feedback that shifts direction reopens it.

When a settled branch is hard to reverse, non-obvious without context, and resolves a real trade-off, invoke **create-adc**. Let **create-adc** handle formatting, numbering, and publishing `~/.astack/<project>/architecture/AD_<N>.md`.

## Research with receipts and keep designs minimal

Dispatch read-only `astack:researcher` subagents (`research-this`, `rtfm`) on upcoming branches while waiting for answers. Weigh evidence in **prove-it** and **research-this** order: live measurements and repo code first, then standards and papers, then external experience reports. Scrutinize user-supplied numbers with the same bar. Run **ab-test** or **benchmarking** when measurements settle a choice, and say plainly when evidence is thin.

Optimize correctness, then robustness, then efficiency, with minimal moving parts. Name concrete mechanisms—data structures, locks, and messages—before inventing labels. Back both pushback and agreement with evidence. Reverse a pick only when you name the new fact that changed it. When the user overrules the evidence, record the overrule and their reasoning as theirs.

## Pause cleanly and hand off to execution

If a session pauses with open branches, save the tree, accepted specs, cost ledger, and pending research outside the repo. Write that snapshot to `~/.astack/<project>/architecture/GRILLING.md` via `astack-tools arch path <project> --ensure` so the next session resumes cleanly.

Once every branch has an accepted spec or explicit deferral, summarize the full design for confirmation. Wait for confirmation before coding. Then hand the settled specs to **dagify** or **treeify** and **lead** for execution.

**Done when:** every branch settles with an accepted spec or deferral, lessons are saved via **lookback**, qualifying ADs are published via **create-adc**, and the user confirms the summary before coding starts.

Referenced skills: `create-adc` (`${CLAUDE_SKILL_DIR}/../create-adc/SKILL.md`), `dagify` (`${CLAUDE_SKILL_DIR}/../dagify/SKILL.md`), `treeify` (`${CLAUDE_SKILL_DIR}/../treeify/SKILL.md`), `research-this` (`${CLAUDE_SKILL_DIR}/../research-this/SKILL.md`), `lookup` (`${CLAUDE_SKILL_DIR}/../lookup/SKILL.md`), `lookback` (`${CLAUDE_SKILL_DIR}/../lookback/SKILL.md`), `prove-it` (`${CLAUDE_SKILL_DIR}/../prove-it/SKILL.md`), `ab-test` (`${CLAUDE_SKILL_DIR}/../ab-test/SKILL.md`), `benchmarking` (`${CLAUDE_SKILL_DIR}/../benchmarking/SKILL.md`), `lead` (`${CLAUDE_SKILL_DIR}/../lead/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts grilling and domain terminology practices from mattpocock/skills and adalundhe/mp-skills (MIT, Copyright (c) 2026 Matt Pocock). See NOTICE.md. -->
