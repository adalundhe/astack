---
name: bugbash
description: "Lead-only vectored debugging workflow: isolate repros, swarm blind investigators, converge, fix, and verify. Use for any reported issue, error, crash, failure, or regression."
disable-model-invocation: true
---

# Bugbash

Lead-only **vectored debugging** workflow for any reported issue, error, crash, failure, regression, or unexpected behavior. For proactive auditing with no specific bug report, use **redteam** instead.

Core rules:

- **Scale investigation to bug risk,** just like **review**. Skip multi-reviewer overhead on an isolated, reproducible bug. Never solo-debug an ambiguous, concurrent, or multi-layer failure.
- **Keep investigators strictly read-only.** Reviewers never write or apply fixes themselves, because mixing guesses with code edits hides the root cause.
- **Shrink the repro first,** because large inputs bury the real trigger in noise.
- **Stop when evidence stalls,** because guessing burns rounds without narrowing the cause.

Follow **lead** for isolated workspaces (**slates** or git worktrees), role timers, watch-and-swap check-ins, and cross-harness "agents as tools" delegation (`astack-dispatch`).

## 1. Assemble the bug dossier fast—never investigate the bug yourself

Collect the report and all linked issues, PRs, docs, logs, traces, metrics, or screenshots. Dispatch `astack-researcher` with `rtfm` or `analyze-environment` when gathering is wide. Never trace code or form root-cause theories before dispatching investigators, because Lead theories bias blind reviewers. Reuse this dossier for investigation and post-fix review.

## 2. Classify bug risk and dispatch read-only investigation vectors

- **Trivial typo** (isolated to one obvious line) or **single-agent host:** skip straight to **find-it** -> **fix-it**.
- **`low` bug** (narrow scope, single clear repro, no concurrency, security, persistence, or cross-layer ambiguity): start with **one** blind read-only `astack-reviewer` running **find-it**. Escalate to multiple vectors below if it cannot reproduce cleanly or surfaces competing causes.
- **`risky` or ambiguous bug** (intermittent, multi-layer, concurrent, persistence/auth/security, or unclear root cause): swarm **at least two** blind read-only reviewers from `reviewer_pool`. Split across **complementary reproduction and investigation methods**, not code folders:
  - end-to-end correlated-data and full-environment replay;
  - boundary, state-transition, and concurrency stress;
  - history, config, and environment bisection;
  - runtime profiling, tracing, and telemetry.

Instruct every investigator to follow **find-it** in order: replicate from real data, **shrink the repro first**, then prove the root cause. Require runnable repros, evidence, and minimal fix proposals with `blast-radius`.

## 3. Converge via peer **challenge** (when multiple vectors ran)

1. **Fresh runs, reset timers:** finished reviewers cannot be messaged in place. Spawn fresh read-only reviewers with reset timers (`reviewer_minutes`) and all peer reports so they disprove weak theories (**challenge**). When competing fixes need runtime comparison, dispatch workers in isolated workspaces and resubmit those workspaces to reviewers.
2. **Stop rule (**decisions-in-plain-words**):**
   - **Converged:** one verified root cause and minimal fix survives. Log every **rejected root-cause theory** and rejected fix approach with disproving evidence as `decided:` in `LANES.md` (`astack-decisions`). Then move to Step 4.
   - **No convergence / stalled:** stop immediately if a round yields no new runnable evidence, hits a product trade-off, or cannot complete further review passes. Escalate plainly with surviving hypotheses, candidate fixes, `blast-radius`, and your recommendation before any worker edits code. Never name configured reviewer model names, pending reviewer rosters, or internal pool state in user replies—even when models fail or are unavailable—because harness internals distract from the decision. Frame remaining uncertainty strictly as bug risk and options.

## 4. Implement via worker (**fix-it**) and resubmit

Dispatch `astack-worker` in an isolated workspace with the converged root cause, shrunk repro, chosen fix, and rejected theories (`decided:`). Require **fix-it** discipline and a report of any **failed fix approaches**. Workers never spawn subagents. Resubmit the worker's workspace to post-fix reviewers.

## 5. Post-fix vectored **review** with **prove-it**

1. Log any worker-reported failed fix approaches as `decided:`.
2. Run vectored **review** (`astack-review-ledger` + `astack-check-gates`). Pass the bug dossier, shrunk repro, rejected theories, and failed fix approaches.
3. Require deterministic **prove-it** verification on the real artifact (plus telemetry frequency where relevant) and concise runnable proof.
4. Route any proven gap back to a fresh worker and resubmit to reviewers until clear.
5. Attach the **prove-it** summary and runnable evidence to any fix PR (`watch-pr`).

## 6. Clean up and close with **lookback** + **make-it-stick**

1. Sweep `no-leaked-secrets` on the diff and PR evidence. Run **cleanup** on `<file>_DEBUG_<shorthash>.<type>` captures and scratch workspaces while preserving PR proof.
2. Run **lookback** over the dossier, shrunk repro, rejected theories, failed fix approaches, and final fix to save or update `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md`.
3. Pair with **make-it-stick** for structural guards. Whenever a guard needs code edits, Lead dispatches a fresh `astack-worker` in an isolated workspace and resubmits it to **review** before landing.

**Reply:** report user-facing facts only. Never name configured reviewer model names, pending reviewer rosters, or internal pool state—even when models fail or are unavailable; frame remaining uncertainty strictly as bug risk and options:
- root cause (or surviving hypotheses if escalated) and the minimal fix;
- shrunk repro and runnable before/after **prove-it** proof;
- remaining bug risk, options if unresolved, and structural guard added.

Referenced skills: `redteam` (`../redteam/SKILL.md`), `review` (`../astack-review/SKILL.md`), `lead` (`../astack-lead/SKILL.md`), `slates` (`../slates/SKILL.md`), `find-it` (`../find-it/SKILL.md`), `fix-it` (`../fix-it/SKILL.md`), `challenge` (`../challenge/SKILL.md`), `decisions-in-plain-words` (`../decisions-in-plain-words/SKILL.md`), `prove-it` (`../prove-it/SKILL.md`), `lookback` (`../lookback/SKILL.md`), `make-it-stick` (`../make-it-stick/SKILL.md`), `cleanup` (`../cleanup/SKILL.md`). Read any cited skill file before acting when its trigger applies.
