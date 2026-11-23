---
name: create-adc
description: "Work out an architecture decision with the person, one evidenced decision at a time, and write it up as the project's next architecture decision document of record (AD-N). Use when the person asks to create, write or grill an architecture decision, an ADC or an AD."
---

# Create ADC

Work the decision out with the person the way a well-tenured architect would, then write it up as the project's next architecture decision: a document of record that says what was decided, why, what it costs, and how to check it.

**Why:** a decision that isn't written down gets argued again, and one written down without its evidence can't be trusted or revisited.

## The design tree

Map the subject as a tree: each decision branches into the decisions that hang off it. Enter what is already settled first, with its receipts: the person's earlier decisions, existing ADs, and anything research or an A/B (**ab-test**) has answered. Then work the open branches, the one with the most riding on it first.

## One exchange per decision

Send one exchange per decision, then wait for the answer:

- **The decision**, plainly, and why it matters now.
- **The evidence**, with numbers.
- **Your recommendation**, or the credible options side by side, argued from practical impact (latency added, failures removed, code avoided), saying which you favour and why.

A decision you can't evidence yet goes back to research, not to the person. Small independent questions may share an exchange; a load-bearing decision goes alone.

## Show, don't tell

Plain words and short sentences, with every term of art defined where it first appears. Demonstrate instead of asserting:

- a difference between options: one concrete scenario walked through each, showing where they split and what each costs there;
- a downside: the failure, played out;
- a benefit: the cost it removes or the failure it survives, played out;
- a conflict: both decisions colliding in one walked scenario.

An adjective with no example ("simpler", "fragile", "scalable") is a claim still owed its demonstration.

## Reconcile every answer

Keep a ledger of the costs accepted with each settled decision. When an answer lands, check it against the ledger for:

- **contradictions** with a settled decision;
- **compounding costs**, each fine alone, together over a budget.

A conflict becomes the next exchange, both decisions named and the joint cost measured. Then grow the tree: enter the decisions the answer now needs, such as lifecycle, states, failure and retry, monitoring and migration. Finding a gap is your job.

## Settling a decision

A chosen direction is not yet settled. Draft its spec for the person to correct:

- an implementation example in the project's stack, small enough to review;
- test cases, each with the failure it catches;
- acceptance criteria, exacting and checkable: a bound, a behaviour under a named condition, an invariant.

A decision is settled when the person accepts its spec. Feedback that reopens the direction reopens the branch.

## Evidence

Research every substantial decision before you argue it, with subagents while the person weighs the current exchange. In order of weight: peer-reviewed work; books and academic texts; engineering reports from companies operating at scale, each one workload's data point; then the local repository, configuration and measurements. Scrutinize the person's own data like any other source. When numbers would move a decision, get them with **ab-test**.

Every recommendation and every pushback carries receipts: a measurement, a bound, a citation, a production number. Say plainly when the evidence is thin.

## What you optimize

Correctness, then robustness, then efficiency, all weighed against size: every component must pay for itself. Name mechanisms concretely (the data structure, the lock, the message) before coining terms for them. Push back with receipts when the evidence disagrees with the person, and prove them right with receipts when it agrees. Change a recommendation only when you can name what changed. The decisions are the person's: record an overrule as theirs, with their reasoning.

## The document of record

1. **Format.** Follow the project's own: read its newest few ADs, often in `docs/architecture/AD_<N>.md`. If it has none, use `template.md` beside this file, in `docs/architecture/`.
2. **Number.** Take the next unused number across the folder and every document that cites AD numbers. A published number never changes; if yours is taken while you draft, take the next free one before publishing.
3. **Draft as you go** in `AD_<N>.draft.md` in the working folder, with the tree: each settled decision with its spec and ledger entry, each open branch and where it stands, research in flight. A later session resumes from it.
4. **Done** when no branch is open: every decision settled with an accepted spec or deferred by the person, every load-bearing one tested against an alternative, nothing assumed. Summarize the design and ask the person to confirm it.
5. **Publish** on their confirmation: Status Accepted with the date; the settled specs in Decision; the ledger in Costs accepted; the rejected alternatives and why; the acceptance criteria, tests and evidence. Then delete the draft.
6. **As built.** When the decision is built, set Status to Built with the date, and add As built (what was really built, aspect by aspect) and Verification (the checks that prove it). Later changes go in dated addenda.

Building it is separate work: its acceptance criteria become the done-whens of the lanes that build it (`/astack-lead`).

<!-- Adapts the grilling skill of mattpocock/skills, as modified in adalundhe/mp-skills (MIT, Copyright (c) 2026 Matt Pocock). See NOTICE.md. -->
