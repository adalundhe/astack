---
name: next-step
description: "Analyze contracts on the stepped-complexity ladder to find minimal, high-value next-step features. Use when researchers or leads recommend new capabilities."
---

# Next step

Examine an implementation and its contracts as a whole through **stepped-complexity**, paired with **delight-users**, to find the highest-value "next step" capabilities on the ladder.

Unlike **rightsize-contracts** (which trims bloat), `next-step` focuses on **expansion**: spotting missing rungs and natural next-tier capabilities that unlock major user value with minimal new surface.

**Primary researcher use:** researchers use this skill alongside **delight-users** when recommending features or interface opportunities.

## 1. Load or build the contract catalog

Check existing contract catalogs under `$HOME/.astack/<project_name>/docs/contracts/` (`astack-tools docs list --project <project_name> --subdir contracts`) and verify them against live code (**rtfm**).

- If missing or stale, catalogue current CLI, TUI, UI, API, config, and env-var contracts per **rightsize-contracts**.
- Save catalogs via `astack-tools docs path <project_name> contracts --file <file> --ensure`. Read-only researchers return the catalog draft and target path for the lead.

## 2. Map current rungs and consumer friction

Map implemented use cases from tests, docs, examples, logs and telemetry (`astack-tools logging list`), user prompts or issues, and source code. Order them on the **stepped-complexity** ladder.

Audit every rung from the consumer's side (**delight-users**):
- Where do users hit an abrupt cliff between a simple built-in flow and manual glue work?
- Which repeated multi-step chores could become one natural step up?
- Which states, feedback signals, error recoveries, or handoffs are missing or awkward?

## 3. Identify minimal-surface next-step opportunities

Look for missing rungs or natural extensions where a small, crisp addition to existing contracts unlocks the next tier of capability without complicating simpler tiers:

- **Compose before inventing:** prefer extending existing primitives or deriving context from existing integrations over bolting on a parallel subsystem (**no-bolt-ons**).
- **Check prior art with receipts:** when comparing approaches or external ecosystems, run **research-this** (A–F graded) and persist findings under `$HOME/.astack/<project_name>/research/` (`astack-tools research path`).
- **Verify zero regression on simpler tiers:** ensure tier $N$ callers stay unchanged when tier $N+1$ lands.

## 4. Rank and present next-step recommendations

Order recommendations by consumer value unlocked relative to new contract surface added. For each proposal, state:

- **Current rung -> Next rung:** what works today vs. the capability unlocked.
- **Minimal contract delta:** exact new API, CLI, UI, or config surface required, and what stays untouched.
- **Consumer delight impact:** concrete friction removed or loop tightened (**delight-users**).
- **Evidence & trade-offs:** `file:line`, telemetry, user signals, or graded **research-this** citations, plus key risks.

Hand approved candidates to **plan-it** for decision shaping or **play-with-me** for a quick interactive prototype.

**Done when:** existing contracts are mapped to ordered tiers, consumer friction is audited via **delight-users**, and next-step opportunities are ranked with minimal contract deltas and primary evidence.

Referenced skills: `stepped-complexity` (`../stepped-complexity/SKILL.md`), `delight-users` (`../delight-users/SKILL.md`), `rightsize-contracts` (`../rightsize-contracts/SKILL.md`), `rtfm` (`../rtfm/SKILL.md`), `no-bolt-ons` (`../no-bolt-ons/SKILL.md`), `research-this` (`../research-this/SKILL.md`), `plan-it` (`../plan-it/SKILL.md`), `play-with-me` (`../play-with-me/SKILL.md`). Read any cited skill file before acting when its trigger applies.
