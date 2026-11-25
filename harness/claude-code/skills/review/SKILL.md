---
name: review
description: "Run vectored adversarial reviews from an approved reviewer_pool in isolated workspaces, gather PR/issue/doc context first, enforce coding rules, prove blocking bugs on rerun, merge overlaps by fix-equivalence, stop via astack-review-ledger, and report only proven findings plainly without leaking internal status. Use before merging or whenever reviewing a branch, diff, code, or PR."
disable-model-invocation: true
---

# Review

Core rules—apply these before anything else:

- **Rerun every finding before keeping it,** because untested claims waste worker cycles.
- **Combine, never vote.** Reproduction is the proof, so a reproduced blocking bug found by one model is just as real.
- **Reviewers never write or apply fixes themselves,** because an author checks what it meant to build. Route fixes to workers to implement and resubmit.
- **Scale rigor to risk.** A low-risk vector stops after one clean review; risky vectors start with at least two blind models.
- **Never treat budget end as approval,** because running out of time proves nothing about the code.

Follow **lead** for isolated workspaces (**slates** or git worktrees), role timers, `LANES.md` check-ins, and cross-harness "agents as tools" delegation via `astack-dispatch`.

## 1. Read scope, `reviewer_pool`, and linked context (**rtfm**, **run-it-back**)

1. Review what the person named; otherwise review all branch changes since base, including uncommitted edits.
2. Read `reviewer_pool` and `reviewer_minutes` from `~/.config/astack/settings.json`. Never dispatch a model outside `reviewer_pool`, because that list decides which vendors see the code. If `reviewer_pool` is absent, treat the active session model as a 1-model pool quietly—never mention a single-model reviewer pool or `settings.json` state as an `"Open Item"`.
3. When any entry targets another harness or provider, check reachability with `astack-dispatch check-pool`. Record unreachable models in `unreachable_models` for `astack-review-ledger` rather than substituting another model.
4. Before dispatching reviewers, read the request, project guides, commit history, PR description, **all PR comments and review threads**, and **every linked issue, PR, discussion, ADR, or spec**. Put those links and settled decisions in every brief so reviewers don't re-ask answered questions.

## 2. Cut vectors and classify risk

Cut the change into review **vectors** with no arbitrary cap (**no-picked-constants**):

- A vector can be a lens (user paths, concurrency/failure modes, coding rules) or a module/path slice.
- A slice is a focus, not a blindfold: every reviewer still sees the whole diff in an isolated workspace.
- **Mandatory `seams` vector:** whenever you slice by path or module, add a `seams` vector covering cross-slice interfaces and invariants via **blast-radius**.
- **Risk level:** mark a vector **`risky`** if it touches shared interfaces, concurrency, persistence, auth/security, or a large diff; otherwise mark it **`low`**.

## 3. Dispatch blind reviewers

1. **Initial models:** start each **`risky`** vector with **at least two** different approved models (because Step 5's stopping estimate needs two). Start each **`low`** vector with **one**. Include a non-worker model whenever `reviewer_pool` allows.
2. **Keep reviewers blind to each other** on the same vector until the batch finishes, because shared findings cause anchoring.
3. **Spawn dedicated reviewers:** Spawn each reviewer with `subagent_type: "astack:reviewer"` in the background (never substitute `general-purpose`), passing its isolated workspace, vector, intent, linked context, repro folder, absolute `skills/` path (`${CLAUDE_SKILL_DIR}/..`), UTC timestamps, and assigned `reviewer_pool` entry—using `astack-dispatch` (see `--help`) for cross-harness models and joining all active runs via `astack-dispatch wait --all --json` before Step 4.
4. **Reviewer instructions:** require **rtfm**, **adversarial-review**, and every matching coding rule from `skills/`. Require standalone failing repro scripts (non-zero on buggy code, 0 when fixed) saved outside `repo/`. For bug fixes, pass the original bug dossier, shrunk repro, rejected theories (`decided:`), and **failed fix approaches/attempts**, requiring **prove-it** verification ready for the PR.
5. **Run the gate tripwire:** run `astack-check-gates <base>..<head>` across the branch/PR range for deleted tests, skips, lint mutes, or loosened tolerances, and still audit test diffs semantically.

## 4. Verify findings and check fix-equivalence

1. Rerun each finding's reproduction as soon as its reviewer finishes, and verify cited contradictions directly. Keep only proven bugs or contradictions; drop unverified claims and lazy questions already answered by linked context. Record blocking, minor, and dropped counts per reviewer.
2. **Count only proven blocking bugs** in stopping math. Report minor suggestions and nits separately so nits never force extra rounds on a clean low-risk vector.
3. **Decide "same bug" by fix-equivalence, never by wording.** Dispatch a worker to apply a minimal candidate fix in a scratch workspace and rerun **both** reproductions against it. Merge them as one root cause only when one fix makes both pass, and log `fix_verified: true` in `equivalence_checks`.
4. **File cross-vector bugs accurately:** if a reviewer proves a blocking bug outside its assigned vector, file it under the vector where its root cause lives.

## 5. Stop per vector with `astack-review-ledger`

Feed `reviewer_pool`, `worker_model`, `unreachable_models`, `vectors`, `equivalence_checks`, and verified counts into `astack-review-ledger` (see `--help` for flags, passing `--calibration ~/.config/astack/calibration.json` when present). Never do stopping math in prose.

Never claim "95% certainty that no bugs remain", because reviewer statistics extrapolate only from bugs these models catch and cannot rule out harder blind spots.

- **`low` vector:** stops after one clean review (non-worker model when available, zero proven blocking bugs). If a blocking bug turns up, add a second approved model and continue below.
- **Blocking bugs found ($D > 0$):** with 2 reviewers, use Chapman plus exact hypergeometric 95% bounds (requiring verified overlap $m \ge 1$ and upper $< 1$). From 3 reviewers on, use **Burnham & Overton's $M_h$ Jackknife** with a **Beta-Binomial $M_h$ profile-likelihood 95% interval**. Stopping (`saturated`) means these models stopped finding new bugs of similar detectability.
- **Zero blocking bugs ($D = 0$) on a `risky` vector:** never pick a guessed detection rate (**no-picked-constants**). If calibrated via `scripts/eval.py --calibrate`, check joint coverage across planted bugs until shared blind spots clear `miss_risk_target` (default `0.05`) or the pool runs out. If uncalibrated, require at least 2 distinct models (non-worker and cross-provider when available) for an honest uncalibrated clean sweep.
- **Run-out pool:** if models run out before a risky vector converges (or only 1 model is reachable), run automated adversarial checks (**full-spectrum-testing** or **formal-validate** / `astack-statechart`) to probe outside LLM blind spots. Keep `landing_blocked: true` until the person chooses to approve more models or accept the risk.

## 6. Report cleanly; keep audit bookkeeping internal

1. Save `astack-review-ledger --markdown` to `<program>/coverage-map.md` and append `--lanes` lines to `LANES.md`. Never quote or link internal audit files in user replies.
2. **Never leak internal review status** to the user. Omit ledger labels (`POOL EXHAUSTED`, `STOPPED (...)`), formulas (`n1/n2/m`, `f1/f2`), coverage-map paths, single-model reviewer pool or `settings.json` defaults, bracketed `[rule: ...]` tags, and model-orchestration narration.
3. **Write plainly (**wat**):** list blocking bugs and contradictions first (impact, both sides of any contradiction, minimal repro/citation, concrete fix), then concise suggestions and nits, then what held. Before posting human-facing PR comments, run **leave-feedback**.
4. Only when `landing_blocked` is true on a risky area, pause landing and ask a plain choice (**decisions-in-plain-words**): proven bugs found, estimated remaining bugs with range, and the choice to approve more models or accept the risk.

## 7. Clean up and close with **lookback**

Run **cleanup** to remove scratch workspaces and temporary files while keeping durable repros and reports. Then run **lookback** into `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md` (paired with **make-it-stick** for recurring guards), skipping a new file only when a clean pass surfaced nothing new.

Referenced skills: `lead` (`${CLAUDE_SKILL_DIR}/../lead/SKILL.md`), `slates` (`${CLAUDE_SKILL_DIR}/../slates/SKILL.md`), `rtfm` (`${CLAUDE_SKILL_DIR}/../rtfm/SKILL.md`), `run-it-back` (`${CLAUDE_SKILL_DIR}/../run-it-back/SKILL.md`), `no-picked-constants` (`${CLAUDE_SKILL_DIR}/../no-picked-constants/SKILL.md`), `blast-radius` (`${CLAUDE_SKILL_DIR}/../blast-radius/SKILL.md`), `adversarial-review` (`${CLAUDE_SKILL_DIR}/../adversarial-review/SKILL.md`), `prove-it` (`${CLAUDE_SKILL_DIR}/../prove-it/SKILL.md`), `full-spectrum-testing` (`${CLAUDE_SKILL_DIR}/../full-spectrum-testing/SKILL.md`), `formal-validate` (`${CLAUDE_SKILL_DIR}/../formal-validate/SKILL.md`), `wat` (`${CLAUDE_SKILL_DIR}/../wat/SKILL.md`), `leave-feedback` (`${CLAUDE_SKILL_DIR}/../leave-feedback/SKILL.md`), `decisions-in-plain-words` (`${CLAUDE_SKILL_DIR}/../decisions-in-plain-words/SKILL.md`), `lookback` (`${CLAUDE_SKILL_DIR}/../lookback/SKILL.md`), `cleanup` (`${CLAUDE_SKILL_DIR}/../cleanup/SKILL.md`), `make-it-stick` (`${CLAUDE_SKILL_DIR}/../make-it-stick/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's interrogate skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
