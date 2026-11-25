---
name: cross-repo
description: "Coordinate multi-repo and multi-step PR merge, IaC, edge, and app deploy trains from one program folder with astack-release: validate the cross-repo DAG and output handoffs, sync PRs via astack-watch-pr, enforce expand-switch-contract deploy gates, and maintain a Mermaid sequence graph plus reverse-order rollback runbook."
disable-model-invocation: true
---

# Cross-repo

Coordinate changes spanning multiple repositories or multi-stage deploy trains from one program folder—preserving deploy order, immutable artifact handoffs, and rollback safety at every step.

## 1. Map repositories, lessons, and handoffs

1. **Discover touched repos and access paths** with `astack-researcher` (**lookup**, **rtfm**, **analyze-environment**). Check `~/.astack/*/lessons/*/LESSON.md` first (`related_projects`, `keywords`) to catch related repos and past traps. Record paths, remotes, review rules, and platform contexts in `TOOLS.md`. Note how each step passes immutable outputs downstream (merge SHA, tag, resource ID, or image digest).
2. **Store the release train in `<program>/release.json`** using `astack-release` (see `--help`). Declare each step's `kind`, `phase` (`expand` | `switch` | `contract` | `general`), `repo`, `env`, `depends_on`, `requires_outputs`, `plan_cmd`, `verify_cmd`, and `rollback_cmd`.

## 2. Plan one ordered cross-repo graph

1. **Plan with **dagify** or **treeify**, anchored by **safe-to-deploy**:** sequence breaking cutovers as **Expand -> Switch & verify -> Contract** across releases. Never assume simultaneous atomic deploys across repos. Keep live workloads and rollbacks working at every intermediate step (**safe-iac**, **least-privilege**).
2. **Pin immutable outputs:** record SHAs, tags, digests, or resource IDs via `astack-release complete --output key=value`. Never pin floating `main` or `latest`, and never store raw secrets (**no-leaked-secrets**).
3. **Audit before editing any repo:** validate acyclicity and ancestor outputs with `astack-release load` and `status`. Then run `astack-reviewer` (**review**) to check **blast-radius**, deploy order, missing consumers, and intermediate rollbacks.

## 3. Execute per-repo lanes with strict DAG gates

Follow **lead** for isolated workspaces (**slates** or git worktrees), read-only reviewers, watch-and-swap clocks, and cross-harness delegation alongside `astack-release`:

1. **Fetch ready steps:** run `astack-release ready <program>/release.json --json` to get steps whose upstream dependencies and `{{step.key}}` outputs are `done`.
2. **One repo per worker:** dispatch each `astack-worker` inside one repo with resolved upstream outputs and `<program>/RELEASE.md`.
3. **Review locally and across seams:** run read-only `astack-reviewer` subagents (**review**) checking repo correctness and compatibility with live upstream/downstream versions.
4. **Gate every PR on upstream steps:** open dependent PRs as Draft or with a hold label (`do-not-merge`/`hold`), never enabling forge auto-merge. Attach PRs (`astack-release set-pr`), watch with `astack-watch-pr --release-file <program>/release.json --release-step <id>`, and sync with `astack-release sync`. Upstream steps must merge and pass `astack-release verify --run` before downstream PRs leave `held`.

## 4. Ship one unified deploy and rollback runbook

Render `<program>/RELEASE.md` with `astack-release render`. Include its Mermaid `flowchart LR` graph in your report and PR descriptions (**show-the-states**, **technical-writing**, **observable-by-default**). Cover merge/apply order, verification between steps (`astack-release verify --run`), reverse-order rollbacks (`astack-release rollback-plan`), and the contract phase.

Once the train finishes or rolls back, run **lookback** into `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md` (listing every touched repo in `related_projects`). Pair with **make-it-stick** for systemic guards.

Referenced skills: `lookup` (`../lookup/SKILL.md`), `rtfm` (`../rtfm/SKILL.md`), `analyze-environment` (`../analyze-environment/SKILL.md`), `dagify` (`../dagify/SKILL.md`), `treeify` (`../treeify/SKILL.md`), `safe-to-deploy` (`../safe-to-deploy/SKILL.md`), `safe-iac` (`../safe-iac/SKILL.md`), `least-privilege` (`../least-privilege/SKILL.md`), `no-leaked-secrets` (`../no-leaked-secrets/SKILL.md`), `review` (`../astack-review/SKILL.md`), `blast-radius` (`../blast-radius/SKILL.md`), `lead` (`../astack-lead/SKILL.md`), `slates` (`../slates/SKILL.md`), `show-the-states` (`../show-the-states/SKILL.md`), `technical-writing` (`../technical-writing/SKILL.md`), `observable-by-default` (`../observable-by-default/SKILL.md`), `lookback` (`../lookback/SKILL.md`), `make-it-stick` (`../make-it-stick/SKILL.md`). Read any cited skill file before acting when its trigger applies.
