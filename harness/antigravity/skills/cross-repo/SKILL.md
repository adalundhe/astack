---
name: cross-repo
description: "Coordinate multi-repo and multi-step PR merge, IaC, edge, and application deploy trains from one program folder using astack-release: validate the cross-repo DAG and upstream output handoffs, sync PRs via astack-watch-pr, enforce expand-switch-contract deploy gates and autonomy boundaries, and maintain a Mermaid sequence graph plus reverse-topological rollback runbook. Use for programs spanning multiple repositories or multi-stage merge/deploy sequences."
disable-model-invocation: true
---

# Cross-repo

Coordinate changes spanning multiple repositories or multi-stage merge/deploy sequences (identity/security repos, cloud/edge IaC, shared packages, GitOps, and application services) from one program folder—preserving strict deploy ordering, immutable artifact handoffs, and rollback safety across every step.

## 1. Map repositories, ownership, and handoff artifacts

1. **Discover all touched repos and access paths** with read-only `astack-researcher` subagents (**lookup**, **rtfm**, **analyze-environment**): consult saved `~/.astack/*/lessons/*/LESSON.md` memories first (`related_projects` & `keywords`) to uncover any related repos and past train lessons, then record every repo's local path/remote, target branch, CI/review rules, target platform contexts (`TOOLS.md`), and how each upstream step hands immutable artifacts downstream (PR merge SHA, git tag, IaC outputs/IDs, chart/package version, image digest, or edge deploy version).
2. **Save the durable release train in the program folder** using `astack-release` (`PATH` or `../../bin/astack-release`): store the validated multi-repo DAG in `<program>/release.json` (plus auto-rendered `<program>/RELEASE.md` with its Mermaid `flowchart LR` sequence diagram, step table, verified cross-repo outputs, and reverse-order rollback plan). Every step declares `kind` (`pr` | `tag` | `deploy` | `verify` | `manual`), `phase` (`expand` | `switch` | `contract` | `general`), `repo`, `env`, `depends_on`, `requires_outputs` (`<upstream_step>.<key>`), `plan_cmd`, `verify_cmd`, and `rollback_cmd`.

## 2. Plan one ordered cross-repo graph

1. **Structure the work with **dagify** or **treeify**, anchored by **safe-to-deploy**:**
   - Sequence breaking cross-repo cutovers strictly as **Expand -> Switch & verify -> Contract** across releases (e.g., *Expand*: create roles/identities -> reference them in security/policy repo via `{{upstream.key}}` -> *Switch*: reference both in app repo + roll out + read-only `verify` confirming zero legacy usage -> *Contract*: retire legacy credentials/paths in a later release).
   - Never assume simultaneous atomic deploys across repos; verify every intermediate state keeps live workloads and rollbacks working (**safe-to-deploy**, **safe-iac**, **least-privilege**).
2. **Pin every cross-repo handoff by immutable ref/output:** record SHAs, tags, chart/package versions, image digests, or resource IDs via `astack-release complete --output key=value` (never floating `main`/`latest`, and never raw secrets—`astack-release` rejects secret-like values per **no-leaked-secrets**).
3. **Audit the cross-repo plan before editing any repo:** validate acyclicity and ancestor output references with `astack-release load`/`status` and dispatch `astack-reviewer` (**review**) to check **blast-radius**, deploy ordering, missing consumers, rollback paths at every intermediate step, and contract alignment across repos.

## 3. Execute per-repo lanes with strict cross-repo gates

Coordinate execution through **lead** using `LANES.md` + `astack-status` watch/swap clocks (`check_in_minutes`, wind-down reminder, fresh successor on overdue runs) alongside `astack-release`:

1. **Discover ready steps with resolved upstream outputs:** run `astack-release ready <program>/release.json --json` to get only steps whose upstream dependencies and required outputs are verified `done`, with `{{step.key}}` references interpolated automatically.
2. **One repo per worker, isolated workspaces:** dispatch each `astack-worker` inside one repository using an isolated **slates** volume (`https://github.com/hyper-light/slates`, preferred when available) or git worktree. Pass resolved upstream outputs and `<program>/RELEASE.md` in its brief.
3. **Review per-repo AND across seams:** run read-only `astack-reviewer` subagents (**review**, never writing fixes themselves—routing fixes to workers to implement and resubmit) checking both repo-local correctness and compatibility with upstream/downstream repos' live versions.
4. **Gate every PR on its upstream DAG + external guards (never auto-merge early):** open dependent PRs as **Draft** or with a hold label (`do-not-merge`/`hold`), **never enable forge auto-merge**, attach opened PRs (`astack-release set-pr`), and watch them with `astack-watch-pr --release-file <program>/release.json --release-step <id>` (plus any `--gate-cmd` external guards CI doesn't know about). Run `astack-release sync <program>/release.json --markdown <program>/RELEASE.md` to sync active PRs: an upstream PR must clear CI, review, approval, merge, **and** any post-merge external verification (`verify_cmd` via `astack-release verify --run`, which holds the step in `verifying` until green) before any downstream dependent PR leaves `held` or advances to `merge_ready`.

## 4. Ship one unified deploy and rollback runbook

Render `<program>/RELEASE.md` with `astack-release render` (and include its Mermaid release-train diagram inline in the user report and PR descriptions per **show-the-states** / **technical-writing** / **observable-by-default**) covering every repo in execution order:
- exact sequence of PR merges, IaC/edge/cluster applies, tags/releases, and DB migrations;
- exact read-only verification command confirming health between each step (`astack-release verify --run`);
- exact reverse-topological rollback procedure at every intermediate stage (`astack-release rollback-plan`);
- explicit follow-up contract/retirement phase once legacy traffic is proven at zero.

Once the multi-repo release train finishes (or rolls back), run **lookback** across `release.json`, PR syncs, deploy/verification outputs, and any rollbacks to save focused `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md` lessons (listing all touched repos in `related_projects`), paired with **make-it-stick** for systemic guards on future trains.

Referenced skills: `lookup` (`../lookup/SKILL.md`), `rtfm` (`../rtfm/SKILL.md`), `analyze-environment` (`../analyze-environment/SKILL.md`), `dagify` (`../dagify/SKILL.md`), `treeify` (`../treeify/SKILL.md`), `safe-to-deploy` (`../safe-to-deploy/SKILL.md`), `safe-iac` (`../safe-iac/SKILL.md`), `least-privilege` (`../least-privilege/SKILL.md`), `no-leaked-secrets` (`../no-leaked-secrets/SKILL.md`), `review` (`../astack-review/SKILL.md`), `blast-radius` (`../blast-radius/SKILL.md`), `lead` (`../astack-lead/SKILL.md`), `slates` (`../slates/SKILL.md`), `show-the-states` (`../show-the-states/SKILL.md`), `technical-writing` (`../technical-writing/SKILL.md`), `observable-by-default` (`../observable-by-default/SKILL.md`), `lookback` (`../lookback/SKILL.md`), `make-it-stick` (`../make-it-stick/SKILL.md`). Read any cited skill file before acting when its trigger applies.
