---
name: cross-repo
description: "Coordinate multi-repo PR merges and staged deploy trains with astack-release and rollback gates. Use for changes spanning multiple repos or deploy stages."
disable-model-invocation: true
---

# Cross-repo

Coordinate changes spanning multiple repositories or multi-stage deploy trains from one program folder. Preserve deploy order, immutable artifact handoffs, and rollback safety at every step.

## 1. Map repositories, lessons, and handoffs

1. **Discover touched repos and access paths** with `astack:researcher` (**lookup**, `rtfm`, `analyze-environment`). Check `~/.astack/*/lessons/*/LESSON.md` first (`related_projects`, `keywords`) for related repos and past traps. Record paths, remotes, review rules, and platform contexts in `<program>/TOOLS.md`. Note each immutable downstream output (merge SHA, tag, resource ID, or image digest).
2. **Store the release train in `<program>/release.json`** using `astack-release`. Run `astack-release --help` for step schema fields (`kind`, `phase`, `depends_on`, outputs, and verification/rollback hooks).

## 2. Plan one ordered cross-repo graph

1. **Plan with `dagify` or `treeify`, anchored by `safe-to-deploy`:** sequence breaking cutovers as **Expand -> Switch & verify -> Contract** across releases. Never assume simultaneous atomic deploys across repos. Keep live workloads and rollbacks working at every step (`safe-iac`, `least-privilege`).
2. **Pin immutable outputs and honor human gates:** record SHAs, tags, digests, or resource IDs via `astack-release complete --output key=value` (or `verify --run --output key=value`). Recorded outputs are immutable once set, and `sync` never copies `head_sha` into `merge_sha`. Never pin floating `main` or `latest`, and never store raw secrets (`no-leaked-secrets`). Record explicit human approvals for gated steps via `astack-release approve --by <approver>`.
3. **Audit before editing any repo:** validate acyclicity and ancestor outputs with `astack-release load <file> --spec <spec.json>` then `astack-release status <file>`. Run `astack:reviewer` (**review**) to check `blast-radius`, deploy order, missing consumers, and intermediate rollbacks.

## 3. Execute per-repo lanes with strict DAG gates

Follow **lead** for isolated workspaces (**slates** or git worktrees), read-only reviewers, watch-and-swap clocks, and cross-harness delegation alongside `astack-release`:

1. **Fetch ready steps:** run `astack-release ready <program>/release.json --json`. Pick steps whose upstream dependencies and `{{step.key}}` outputs are `done`.
2. **One repo per worker:** dispatch each `astack:worker` inside one repo with resolved upstream outputs and `<program>/RELEASE.md`.
3. **Review locally and across seams:** run read-only `astack:reviewer` subagents (**review**). Check repo correctness and compatibility with live upstream and downstream versions.
4. **Gate every PR on upstream steps:** open dependent PRs as Draft or with a hold label (`do-not-merge`/`hold`). Never enable forge auto-merge, because out-of-order merges break live consumers. Attach PRs (`astack-release set-pr`), watch with `astack-watch-pr --release-file <program>/release.json --release-step <id>`, and sync with `astack-release sync`. Upstream steps must reach `done` (with `astack-release verify --run` passing on every step that defines `verify_cmd`) before downstream PRs leave `held`.

## 4. Ship one unified deploy and rollback runbook

Render `<program>/RELEASE.md` with `astack-release render`. Include its Mermaid `flowchart LR` graph in your report and PR descriptions (`show-the-states`, `technical-writing`, `observable-by-default`). Document merge order, verification (`astack-release verify --run`), reverse-order rollbacks (`astack-release rollback-plan`, `unland`), and the contract phase.

Once the train finishes or rolls back, run **lookback** into `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md` (listing every touched repo in `related_projects`). Pair with **make-it-stick** for systemic guards.

**Done when:** every step reaches `done` in dependency order (with `astack-release verify --run` passing on every step that defines `verify_cmd`), `<program>/RELEASE.md` has the Mermaid graph and rollback plan, and **lookback** recorded the lesson.

Referenced skills: `lookup` (`${CLAUDE_SKILL_DIR}/../lookup/SKILL.md`), `review` (`${CLAUDE_SKILL_DIR}/../review/SKILL.md`), `lead` (`${CLAUDE_SKILL_DIR}/../lead/SKILL.md`), `slates` (`${CLAUDE_SKILL_DIR}/../slates/SKILL.md`), `lookback` (`${CLAUDE_SKILL_DIR}/../lookback/SKILL.md`), `make-it-stick` (`${CLAUDE_SKILL_DIR}/../make-it-stick/SKILL.md`). Read any cited skill file before acting when its trigger applies.
