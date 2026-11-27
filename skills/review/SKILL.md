---
name: review
description: "Run repo-native verification and blind reviews from reviewer_pool, prove bugs on rerun, and stop via ledger. Use before merging or reviewing any branch, diff, or PR."
disable-model-invocation: true
---

# Review

Core rules—apply these first:

- **Rerun every finding before keeping it,** because untested claims waste worker cycles.
- **Combine, never vote.** Reproduction is proof, so one model's reproduced blocker is real.
- **Reviewers never write or apply fixes themselves,** because an author checks what it meant to build. Route fixes to workers to implement and resubmit.
- **Verify stateful and concurrent seams with native tools first.** Use each repository's real toolchain (property tests, concurrency harnesses, fuzzers, differential checks, or TLA+ via `astack-statechart`) instead of prose-only sweeps.
- **Scale rigor to risk.** Score vectors in `[0, 1)` via **risk-modeling** and allocate reviewers from fault mass. A verified zero-risk change stops after one clean review.
- **Never treat budget end as approval,** because running out of time proves nothing. Report skipped checks plainly under `Not checked`.

Follow **lead** for isolated workspaces (**slates** or git worktrees), role timers, `LANES.md` check-ins, and cross-harness "agents as tools" via `astack-dispatch`.

## 1. Read scope, `reviewer_pool`, and linked context (**rtfm**)

1. Review what the person named. Otherwise review all branch changes since base, including uncommitted edits.
2. Read `reviewer_pool` and `reviewer_minutes` from `~/.config/astack/settings.json`. Never dispatch outside `reviewer_pool`, because it controls which vendors see code. If unset, use the active session model as a 1-model pool quietly—never flag a single-model reviewer pool or `settings.json` state as an `"Open Item"`.
3. For cross-harness entries, run `astack-dispatch check-pool`. Log unreachable models in `unreachable_models` for `astack-review-ledger` instead of substituting.
4. Read project guides, saved `~/.astack/<project>/` decisions, reviews, and repros (**lookup**), git history, PR description, **all PR comments and review threads**, and **every linked issue, PR, discussion, repo ADR, or spec**. Pass those links and settled decisions in every brief so reviewers skip answered questions.

## 2. Triage the diff, cut vectors, and score risk (**risk-modeling**)

Inspect the git diff directly as Lead (or via a read-only `astack:researcher` using **blast-radius**):

- **Cut behavioral vectors:** slice along real failure faces (concurrency, persistence, auth, interfaces, cross-module seams). Add a `seams` vector whenever you slice by path or module. Every reviewer still sees the whole diff in an isolated workspace.
- **Score vectors in `[0, 1)`:** run `astack-review-ledger score --repo <repo> --base <base> --head <head> --json` for the additive git baseline. It authorizes **shares** and emits `gap_atoms`. Inspect diffs in the repo's language for contract changes: changed signatures, error variants, ordering or lock edits, edited test assertions, or review-fix rework. Pass those signals via per-atom `extra_features` or `gap_mass` per **risk-modeling**. Use `risk: 0.0` only for empty or verified non-behavioral changes.
- **Identify high-risk stateful seams:** flag shared mutable state, lock boundaries, WAL/persistence rollback, async races, and state machines for native executable verification (property tests, concurrency/loom/race harnesses, fuzzers, differential tests, or TLA+ via `astack-statechart` / **formal-validate**).

## 3. Run native checks and dispatch blind reviewers

1. **Verify high-risk seams with repo-native tools first:**
   - Build executable checks in the repository's own toolchain when reading miss is high or a diff touches concurrency, persistence, or protocol invariants. Use `cargo test`/`loom`/`proptest`, `go test -race`, `fast-check`, `hypothesis`, fuzzers, mutation checks, or TLA+ via `astack-statechart`.
   - Keep reviewer harnesses and repros strictly outside `repo/` under `astack-tools repros path <project> --ensure`. Dispatch an `astack:worker` targeting `ASTACK_HOME` when builds need write access. Never edit target repo files during review.
2. **Allocate reviewers from fault mass and dynamic gap share:**
   - **Zero-risk (`risk: 0.0`) or verified seam-backed vector:** start with **one** non-worker model.
   - **Positive-risk vector (`risk > 0`):** never cap Wave 1 at two reviewers. Call `astack-review-ledger --outcomes ~/.astack/<project>/reviews/scorer_outcomes.jsonl` when outcomes exist. Pass `reviews: []`, `budget`, scored `vectors` (including `gap_mass` and any lead- or test-proven `known_blockers`), `catch_table`, and `reviewer_pool`. Greedy risk-scaled Wave 1 gives top-risk vectors 3, 4, or more models while protecting blind spots. Closed clean vectors return their slots (`returned_slots`). Reviewer-, lead-, or seam-proven blockers trigger inline gap-weight refresh, parallel secondary expansion, and evidence-driven capacity recharge (strictly capped by optional `max_budget_minutes`).
3. **Keep reviewers blind to each other and honor per-reviewer brief modes:** stay blind until the batch finishes, because shared findings cause anchoring. Assign orthogonal lenses across blind reviewers. Check each model's `brief_mode` in `next_actions` and inspect `gap_atoms`. Multi-reviewer gap vectors assign one `gap_brief` infielder while other models run standard sweeps. One-reviewer gap vectors use `standard_with_gap_focus` for full standard sweeps plus gap focus. If a model blocks or fails, log it in `failed_reviews` (and `unreachable_models` if global) with each finished reviewer's `brief_mode`. Re-run `astack-review-ledger` to transfer lost slots to another reachable approved model.
4. **Spawn dedicated reviewers:** allocate a review bundle (`astack-tools reviews path <project> --new --ensure`) and repro folder (`astack-tools repros path <project> --ensure`). Spawn each reviewer with `subagent_type: "astack:reviewer"` in the background (never substitute `general-purpose`). Pass the resolved absolute `skills/` path (`astack-tools skills-dir`, never `..`), isolated workspace, vector, intent, linked context, review evidence folder, UTC timestamps, and assigned `reviewer_pool` entry. Pass `--review-dir`, `--repro-dir`, and `--brief-mode` to `astack-dispatch` for cross-harness models. Join active runs via `astack-dispatch wait --all --json` with a bounded `--timeout` before Step 4.
5. **Reviewer instructions:** require **rtfm**, **adversarial-review**, and every matching coding rule. Save raw artifacts per `prove-it` in the review bundle. Save standalone failing repros (non-zero on buggy code, `0` when fixed) in the repro folder. For bug fixes, pass the dossier, shrunk repro, rejected theories (`decided:`), and failed fix approaches/attempts.
6. **Run the gate tripwire:** run `astack-check-gates <base>..<head>` for deleted tests, skips, lint mutes, or loosened tolerances. Audit test diffs semantically too.

## 4. Verify findings and check fix-equivalence

1. Inspect each reviewer's saved bundle and repros. Rerun every finding's repro and verify cited contradictions directly. Keep only proven bugs or contradictions backed by real evidence. Drop unverified claims and answered questions.
2. **Count only proven blocking bugs (`P0–P2`)** in stopping math. Report `P3–P5` suggestions and nits separately so minor items never trigger extra rounds.
3. **Decide "same bug" by fix-equivalence, never wording.** Have a worker apply a minimal fix in a scratch workspace and rerun **both** repros. Merge them only when one fix makes both pass, logging `fix_verified: true` in `equivalence_checks`.
4. **File cross-vector bugs accurately.** File bugs proven outside an assigned vector under their root-cause vector.

## 5. Stop per vector with `astack-review-ledger`

Feed `reviewer_pool`, `worker_model`, `unreachable_models`, `budget`, scored `vectors` (`risk` in `[0, 1)`, `mass`, `commit_masses`, `phi`, `target`, `finder_checks`), `catch_table`, optional `seams` verdicts, `equivalence_checks`, `reviews` (with `brief_mode`), and `failed_reviews` into `astack-review-ledger`. Pass `--receipts <review_dir>` so blocked or failed dispatch receipts ingest automatically. Never do stopping math in prose.

- **Repo-local calibration (agent-directed):** to anchor or measure `catch_table` on this repository, replay real historical bugs (or diff-local seeds surviving existing tests) through this same review flow, and grade each catch mechanically with two trees and exit codes (fails on buggy tree, passes on fixed tree). Never rely on a synthetic single-language fixture for absolute catch levels.
- **Never claim "95% certainty that no bugs remain",** because statistics extrapolate only from bugs these models catch.
- **Ledger loop rule:** when `overall == "continue"` and `next_actions` names reachable models, dispatch that next wave before finalizing—unless the person asked to stop on first blockers or measured budget expired (list unfinished areas under `Not checked`).
- **Blocking bugs found (`D > 0`):** let `astack-review-ledger` judge saturation (Chapman + exact hypergeometric bounds at 2 models; Jackknife Mh + Beta-Binomial bounds at 3+). When models find disjoint singletons, Wave 2 expands in parallel from `estimated_unfound` and recharges budget automatically. Unanimous small counts dispatch one confirming model. When all reachable models agree unanimously with zero singletons, fix the proven bug and re-review the fix.
- **Zero blockers (`D = 0`) on positive-risk vectors:** read the honest `residual_risk` and `residual_risk_bracket` (`prior` or `anchored` tables leave off-anchor point risk `null`). Never claim certainty from unmeasured catch rates.
- **Run-out pool:** if models run out early (or only 1 is reachable), run **full-spectrum-testing** or **formal-validate** / `astack-statechart`. Keep `landing_blocked: true` until the person approves more models or accepts the risk.

## 6. Report cleanly; keep audit bookkeeping internal

1. Save `astack-review-ledger --markdown` to `<program>/coverage-map.md` and append `--lanes` lines to `LANES.md`. Append `outcome_record` to `~/.astack/<project>/reviews/scorer_outcomes.jsonl` once blockers settle. Never quote or link internal audit files to the user.
2. **Never leak internal review status.** Omit ledger labels (`POOL EXHAUSTED`, `STOPPED (...)`), formulas (`n1/n2/m`, `f1/f2`), coverage-map paths, model rosters, single-model reviewer pool, `settings.json` defaults, `[rule: ...]` tags, and orchestration narration.
3. **Write plainly (`wat`):** present findings with their reviewer-assigned `P0–P5` impact tags to both workers and users. List `P0–P2` blocking bugs and contradictions first (impact, both sides, repro/citation, concrete fix). Then list `P3–P5` suggestions and nits, what held, `"Holds only while:"` conditions, and `Not checked` / `Could not check` in plain words. Audit PR comments via **leave-feedback** before posting.
4. When `landing_blocked` is true on a risky area, pause landing and ask a plain choice (`decisions-in-plain-words`): proven bugs, estimated remaining range or failing checks, and whether to approve deeper verification or accept risk.

## 7. Clean up and close with **lookback**

Run `cleanup` on scratch workspaces and repo-local temp files while keeping durable review bundles (`~/.astack/<project>/reviews/<date_time>/`) and project repros (`~/.astack/<project>/repros/`). Then run **lookback** into `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md`, paired with `make-it-stick` for recurring guards. Skip a new lesson only when nothing new surfaced.

<!-- Adapts pstack's interrogate skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
