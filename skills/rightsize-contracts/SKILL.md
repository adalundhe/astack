---
name: rightsize-contracts
description: "Catalogue user contracts, map stepped-complexity tiers, and recommend surface reductions. Use during reviews or audits to simplify CLI, UI, API, and config contracts."
disable-model-invocation: true
---

# Rightsize contracts

Audit every user-facing and caller-facing contract through **stepped-complexity**, then recommend specific ways to cut surface area and align each touchpoint to its tier.

**Primary reviewer use:** reviewers run this skill during worker implementation reviews (**adversarial-review**) to recommend evidenced user-facing complexity and interface reductions.

## 1. Observe and catalogue contracts

Inspect every place the codebase establishes a contract with end users or callers—CLIs, subcommands, flags, TUIs, UIs, APIs/SDKs, config files, env vars, error formats, and exit codes (illustrative, never exhaustive).

- Persist the catalog under `$HOME/.astack/<project_name>/docs/contracts/<file>` (`%USERPROFILE%\.astack\<project_name>\docs\contracts\<file>` on Windows; `ASTACK_HOME` overrides).
- Resolve paths via `astack-tools docs path <project_name> contracts --file <file> --ensure`. Check existing catalogs first via `astack-tools docs list --project <project_name> --subdir contracts`.
- Read-only roles (reviewers and researchers) never edit repo files or write directly to `docs/contracts/`. Always return the catalog draft and target path for the lead to persist (reviewers may keep a supporting copy in `reviews/<date_time>/`).

## 2. Map contracts to real use cases

Trace every catalogued touchpoint against tests, documentation, examples, logs and telemetry (`astack-tools logging list`), user inputs or issues, and the implementation itself (**rtfm**).

- Cite exact `file:line` contract definitions alongside the real use cases they serve.
- Flag orphaned, duplicated, or undocumented touchpoints explicitly.

## 3. Order use cases on the stepped-complexity ladder

Order the mapped use cases from simplest to most advanced based on how each builds on the previous tier (**stepped-complexity**).

- Verify that moving one rung up requires only the minimal new surface.
- Highlight cliffs, duplicated paths, or tiers forced to supply data meant for a higher tier.

## 4. Spot reduction and alignment opportunities

Examine every touchpoint to maximize each step's reach while cutting surface count and complexity. Watch for (illustrative, never exhaustive):

- unclear or inconsistent naming across tiers;
- hidden side effects or overloaded, counterintuitive behaviors;
- hidden surface interfaces (undocumented env vars, implicit toggles, magic paths; **no-hidden-config**);
- excessive nesting or optionality—too many flags on a CLI command, or deeply nested structures in one API handling distinct complexity tiers;
- redundant configuration options asking for data already derivable programmatically from existing integrations, code, or runtime resources;
- parallel bolt-on modes, legacy shims, or dead flags (**no-bolt-ons**, **yagni**).

## 5. Recommend specific, safe reductions

Ground every recommendation in observed files and mapped tiers, never vague complaints:

- **Touchpoint & current tier(s):** exact `file:line` and which use cases depend on it.
- **Complexity defect:** what is bloated, overloaded, hidden, or redundant.
- **Proposed right-sized contract:** exact target shape showing how each tier extends the one below it (**delight-users**).
- **Migration safety:** note any compatibility or rollout steps needed for live callers (**safe-to-deploy**).

**Done when:** contracts are catalogued under `$HOME/.astack/<project_name>/docs/contracts/` (or drafted for the lead), mapped to ordered complexity tiers, and backed by evidenced interface-reduction recommendations.
