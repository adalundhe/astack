---
name: astack-review
description: "Run blind vectored adversarial reviews from reviewer_pool, prove bugs on rerun, and stop via ledger. Use before merging or reviewing any branch, diff, or PR."
disable-model-invocation: true
---

# Review

Core rules—apply these first:

- **Rerun every finding before keeping it,** because untested claims waste worker cycles.
- **Combine, never vote.** Reproduction is proof, so one model's reproduced blocker is real.
- **Reviewers never write or apply fixes themselves,** because an author checks what it meant to build. Route fixes to workers to implement and resubmit.
- **Scale rigor to risk.** A low-risk vector stops after one clean review. Risky vectors start with at least two blind models.
- **Never treat budget end as approval,** because running out of time proves nothing.

Follow **lead** for isolated workspaces (**slates** or git worktrees), role timers, `LANES.md` check-ins, and cross-harness "agents as tools" via `astack-dispatch`.

## 1. Read scope, `reviewer_pool`, and linked context (**rtfm**)

1. Review what the person named. Otherwise review all branch changes since base, including uncommitted edits.
2. Read `reviewer_pool` and `reviewer_minutes` from `~/.config/astack/settings.json`. Never dispatch outside `reviewer_pool`, because it controls which vendors see code. If unset, use the active session model as a 1-model pool quietly—never flag a single-model reviewer pool or `settings.json` state as an `"Open Item"`.
3. For cross-harness entries, run `astack-dispatch check-pool`. Log unreachable models in `unreachable_models` for `astack-review-ledger` instead of substituting.
4. Read project guides, saved `~/.astack/<project>/` decisions, reviews, and repros (**lookup**), git history, PR description, **all PR comments and review threads**, and **every linked issue, PR, discussion, repo ADR, or spec**. Pass those links and settled decisions in every brief so reviewers skip answered questions.

## 2. Cut vectors and classify risk

Cut the change into review **vectors** with no arbitrary cap:

- A vector is a lens (user paths, concurrency, failure modes, coding rules) or a module slice.
- Every reviewer still sees the whole diff in an isolated workspace.
- **Mandatory `seams` vector:** whenever you slice by path or module, add a `seams` vector via **blast-radius**.
- **Risk level:** mark a vector **`risky`** if it touches shared interfaces, concurrency, persistence, auth/security, or a large diff. Otherwise mark it **`low`**.

## 3. Dispatch blind reviewers

1. **Initial models:** start each **`risky`** vector with **at least two** approved models (Step 5 needs two). Start each **`low`** vector with **one**. Include a non-worker model when `reviewer_pool` allows.
2. **Keep reviewers blind to each other** on the same vector until the batch finishes, because shared findings cause anchoring.
3. **Spawn dedicated reviewers:** Allocate a review evidence folder (`astack-tools reviews path <project> --new --ensure`) and project repro folder (`astack-tools repros path <project> --ensure`). Spawn each reviewer as the `astack-reviewer` subagent in the background (never substitute `generalPurpose`). Pass the resolved absolute `skills/` path (`astack-tools skills-dir`, never `..`), isolated workspace, vector, intent, linked context, review evidence folder, UTC timestamps, and assigned `reviewer_pool` `model`. Pass `--review-dir` and `--repro-dir` to `astack-dispatch` (see `--help`) for cross-harness models. Join all active runs via `astack-dispatch wait --all --json` before Step 4.
4. **Reviewer instructions:** require **rtfm**, **adversarial-review**, and every matching coding rule. Require reviewers to save runtime artifacts (traces, logs, metrics, monitoring data, screenshots, profiles, benchmarks) in the review bundle and standalone failing repros (non-zero on buggy code, `0` when fixed) in the repro folder. For bug fixes, pass the dossier, shrunk repro, rejected theories (`decided:`), and **failed fix approaches/attempts**, requiring `prove-it` PR verification.
5. **Run the gate tripwire:** run `astack-check-gates <base>..<head>` for deleted tests, skips, lint mutes, or loosened tolerances. Audit test diffs semantically too.

## 4. Verify findings and check fix-equivalence

1. Inspect each reviewer's saved bundle and repros, rerun every finding's repro, and verify cited contradictions directly. Keep only proven bugs or contradictions backed by real evidence. Drop unverified claims and answered questions, and record blocking, minor, and dropped counts.
2. **Count only proven blocking bugs** in stopping math. Report suggestions and nits separately so nits never trigger extra rounds.
3. **Decide "same bug" by fix-equivalence, never wording.** Have a worker apply a minimal fix in a scratch workspace and rerun **both** repros. Merge them only when one fix makes both pass, logging `fix_verified: true` in `equivalence_checks`.
4. **File cross-vector bugs accurately.** File bugs proven outside an assigned vector under their root-cause vector.

## 5. Stop per vector with `astack-review-ledger`

Feed `reviewer_pool`, `worker_model`, `unreachable_models`, `vectors`, `equivalence_checks`, and verified counts into `astack-review-ledger` (pass `--calibration ~/.config/astack/calibration.json` when present). Never do stopping math in prose.

Never claim "95% certainty that no bugs remain", because statistics extrapolate only from bugs these models catch.

- **`low` vector:** stops after one clean review (non-worker model when available, zero blockers). If a blocker appears, add a second model and continue below.
- **Blocking bugs found (D > 0):** let `astack-review-ledger` judge saturation (Chapman + hypergeometric bounds at 2 reviewers; Burnham–Overton Jackknife + Beta-Binomial bounds at 3+). `saturated` means these models stopped finding similar bugs.
- **Zero blockers (D = 0) on `risky`:** never pick a guessed catch rate. Use `scripts/eval.py --calibrate` data when present. Otherwise require at least 2 distinct models (non-worker and cross-provider when available).
- **Run-out pool:** if models run out early (or only 1 is reachable), dispatch a reviewer or worker for `full-spectrum-testing` or `formal-validate` / `astack-statechart`. Keep `landing_blocked: true` until the person approves more models or accepts the risk.

## 6. Report cleanly; keep audit bookkeeping internal

1. Save `astack-review-ledger --markdown` to `<program>/coverage-map.md` and append `--lanes` lines to `LANES.md`. Never quote or link internal audit files to the user.
2. **Never leak internal review status.** Omit ledger labels (`POOL EXHAUSTED`, `STOPPED (...)`), formulas (`n1/n2/m`, `f1/f2`), coverage-map paths, model rosters, single-model reviewer pool, `settings.json` defaults, `[rule: ...]` tags, and orchestration narration.
3. **Write plainly (`wat`):** list blocking bugs and contradictions first (impact, both sides, repro/citation, concrete fix), then suggestions and nits, then what held. Audit PR comments via **leave-feedback** before posting.
4. When `landing_blocked` is true on a risky area, pause landing and ask a plain choice (`decisions-in-plain-words`): proven bugs, estimated remaining range, and whether to approve more models or accept risk.

## 7. Clean up and close with **lookback**

Run `cleanup` on scratch workspaces and repo-local temp files while keeping durable review bundles (`~/.astack/<project>/reviews/<date_time>/`) and project repros (`~/.astack/<project>/repros/`). Then run **lookback** into `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md`, paired with `make-it-stick` for recurring guards. Skip a new lesson only when nothing new surfaced.

Referenced skills: `lead` (`../astack-lead/SKILL.md`), `slates` (`../slates/SKILL.md`), `rtfm` (`../rtfm/SKILL.md`), `lookup` (`../lookup/SKILL.md`), `blast-radius` (`../blast-radius/SKILL.md`), `adversarial-review` (`../adversarial-review/SKILL.md`), `leave-feedback` (`../leave-feedback/SKILL.md`), `lookback` (`../lookback/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's interrogate skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
