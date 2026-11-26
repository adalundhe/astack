---
name: create-adc
description: "Author, number, publish, and maintain architecture decision docs (AD_<N>.md) from settled design specs. Use when recording or updating an architecture decision."
disable-model-invocation: true
---

# Create ADC

Author, publish, and maintain architecture decision documents (`AD_<N>.md`). Record what was decided, why, what it costs, how to verify it, and how the built code compares.

If the underlying design still has open branches, unexamined alternatives, or missing acceptance criteria, run **plan-it** first. Let **plan-it** grill, narrow, and settle the design; this skill owns the AD document lifecycle.

## Qualification and cross-OS path

Publish an `AD_<N>.md` only when all three hold: hard to reverse, non-obvious without context, and the result of a real trade-off. Follow [AD_FORMAT.md](./AD_FORMAT.md).

Store architecture decisions under `~/.astack/<project>/architecture/AD_<N>.md`. That path resolves cross-OS (`$HOME/.astack` on POSIX, `%USERPROFILE%\.astack` on Windows, honoring `ASTACK_HOME`). Resolve and create the directory with `astack-tools arch path <project> --next --ensure`. If a repository already maintains its own AD folder, match its layout and numbering.

## Numbering, drafting, and publishing

Claim the next unused `ad_number` across the architecture directory and any documents citing AD numbers. Published numbers never change. If drafting spans sessions and that number gets taken, bump to the next free number before publishing.

Draft incrementally in `AD_<N>.draft.md` beside the target path when work spans multiple exchanges. Follow [AD_FORMAT.md](./AD_FORMAT.md) for every section. Ground `Context` in a walked scenario with code paths and numbers. Put concrete mechanisms, diagrams, and implementation sketches in `Decision`. Copy ledger entries into `Costs accepted`, and log rejected options (plus any user overrules and reasoning) under `Alternatives considered`. Include checkable `Acceptance criteria`, `Tests`, and `Evidence`.

Ask the user to confirm before publishing. On confirmation, set `## Status` to `Accepted (<YYYY-MM-DD>)`, write `AD_<N>.md`, and delete `AD_<N>.draft.md`.

## As-built upkeep

Implementation is separate work: the AD's acceptance criteria become the done-when checks for **dagify** and **lead**. Once built, update `## Status` to `Built (<YYYY-MM-DD>)`, or append a dated `As built` addendum. Record the actual modules built, any verified deviations, and the checks proving equivalence or invariants.

**Done when:** the qualifying `AD_<N>.md` is published at the next unused cross-OS path per [AD_FORMAT.md](./AD_FORMAT.md), confirmed by the user, and any draft file is removed.

<!-- Adapts architecture decision record workflows alongside plan-it. See NOTICE.md. -->
