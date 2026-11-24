---
name: create-adc
description: "Work through an architecture decision with the person one evidenced question at a time and write it up as the next AD-N document. Use when asked to draft, review, or grill an architecture decision (ADC/AD)."
disable-model-invocation: true
---

# Create ADC

Work out an architecture decision with the person one step at a time, then publish it as the project's next architecture decision document (`AD-<N>`): what was decided, why, what it costs, and how to verify it.

## The design tree

Map the problem as a dependency tree where each decision branches into downstream choices. Fill in what's already settled first, with citations: earlier decisions, existing ADs, and anything answered by research or an A/B (**ab-test**). Work open branches highest-impact first.

## One exchange per decision

Send one focused exchange per decision, then wait for the answer:

- **The decision** in plain terms and why it matters now.
- **The evidence** with concrete numbers or citations.
- **Your recommendation** (or credible options side by side), argued from practical impact (latency, failure modes removed, code avoided), stating which option you favor and why.

If you don't have solid evidence yet, go research it instead of asking. Small independent questions may share an exchange; load-bearing decisions go one at a time.

## Show, don't tell

Use short sentences and define domain terms where they first appear. Demonstrate trade-offs instead of asserting adjectives:

- **Difference between options:** walk one concrete scenario through both and show where they diverge and what each costs.
- **Downside:** play out the concrete failure.
- **Benefit:** show the specific cost removed or failure survived.
- **Conflict:** walk one scenario where two decisions collide.

Any bare adjective ("simpler", "fragile", "scalable") needs a concrete example.

## Reconcile every answer

Maintain a running ledger of costs accepted with each settled decision. After each answer, check the ledger for:

- **contradictions** with an already-settled decision;
- **compounding costs** that look fine individually but exceed a budget together.

Turn any conflict into the next exchange, naming both decisions and their combined cost. Then expand the tree with new decisions the answer implies (lifecycle, states, failure/retry, monitoring, migration). Surfacing gaps is your job.

## Settling a decision

Choosing a direction doesn't settle a branch. Draft a concrete spec for the person to review or adjust:

- a small implementation sketch in the project's stack;
- specific test cases and the failures each catches;
- checkable acceptance criteria (bounds, behavior under named conditions, invariants).

A branch is settled only once the person accepts its spec. Feedback that changes direction reopens the branch.

## Evidence

Research every major decision before arguing it—spawn read-only subagents while waiting on the current exchange. Weigh sources in order: peer-reviewed papers, textbooks, scale engineering reports (noting each reflects a single workload), then the local repo, config, and measurements. Scrutinize the person's own numbers with the same skepticism. When benchmarks would move a decision, run **ab-test**.

Back every recommendation and pushback with concrete evidence (a measurement, bound, citation, or production figure), and state plainly when evidence is thin.

## What to optimize

Optimize correctness, then robustness, then efficiency, weighed against complexity: every added component must earn its keep. Name concrete mechanisms (the data structure, lock, or message) before inventing terminology. Push back with evidence when the data disagrees with the person, and confirm with evidence when it agrees. Change your recommendation only when you can name what new fact changed it. The person makes the final call—if they overrule your recommendation, record their decision and reasoning.

## The document of record

1. **Format:** match the project's existing ADs (commonly `docs/architecture/AD_<N>.md`). If none exist, use `template.md` beside this file under `docs/architecture/`.
2. **Numbering:** claim the next unused number across the folder and any documents citing AD numbers. Published numbers never change; if your number is taken while drafting, bump to the next free one before publishing.
3. **Draft incrementally** in `AD_<N>.draft.md` in the working folder: track the tree, settled specs, cost ledger, open branches, and in-flight research so a later session can resume cleanly.
4. **Confirm when done:** once every branch is settled with an accepted spec (or explicitly deferred), every load-bearing choice has been weighed against alternatives, and nothing is assumed, summarize the whole design and ask for confirmation to publish.
5. **Publish** on confirmation: set Status to `Accepted (<date>)`, copy settled specs into `Decision`, the ledger into `Costs accepted`, rejected alternatives with reasons, acceptance criteria, tests, and evidence, then delete the draft.
6. **Track as-built state:** once implemented, update Status to `Built (<date>)` and add `As built` (actual implementation aspect by aspect) and `Verification` (checks proving it). Record later changes in dated addenda.

Implementation is separate work: the AD's acceptance criteria become the done-when checks of the lanes that build it (`/astack:lead`).

Referenced skills: `ab-test` (`${CLAUDE_SKILL_DIR}/../ab-test/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts the grilling skill of mattpocock/skills, as modified in adalundhe/mp-skills (MIT, Copyright (c) 2026 Matt Pocock). See NOTICE.md. -->
