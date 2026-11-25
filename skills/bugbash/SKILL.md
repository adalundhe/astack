---
name: bugbash
description: "Default lead-only vectored bug workflow for any reported issue, error, crash, failure, regression, or unexpected behavior: assemble the dossier, classify bug risk, run 1 blind read-only reviewer for isolated low-risk bugs or swarm >=2 across complementary reproduction vectors for risky/ambiguous bugs (find-it), converge via peer challenge, fix via worker (fix-it), verify via post-fix review (prove-it + PR proof), and close with lookback + make-it-stick."
disable-model-invocation: true
---

# Bugbash

Lead-only **vectored debugging** workflow for any reported issue, error, crash, failure, regression, or unexpected behavior. For proactive auditing of an existing codebase with no specific bug report, use **redteam** instead.

Core rules:

- **Scale investigation to bug risk,** just like **review**. Don't pay multi-reviewer swarm overhead on an isolated, reproducible bug; don't solo-debug an ambiguous, concurrent, or multi-layer failure.
- **Keep investigators strictly read-only.** Reviewers never write or apply fixes themselves, because mixing guesses with code edits hides the root cause.
- **Shrink the repro first,** because large inputs bury the real trigger in noise.
- **Stop when evidence stalls,** because guessing burns rounds without narrowing the cause.

Follow **lead** for isolated workspaces (**slates** or git worktrees), role timers, watch-and-swap check-ins, and cross-harness "agents as tools" delegation (`astack-dispatch`).

## 1. Assemble the bug dossier fast—never investigate the bug yourself

Collect the report and all linked issues, PRs, docs, logs, traces, metrics, or screenshots. Dispatch `astack:researcher` with **rtfm** or **analyze-environment** if gathering is wide. Don't trace code or form root-cause theories yourself before dispatching investigators, because lead theories bias blind reviewers. Reuse this dossier for both investigation and post-fix review.

## 2. Classify bug risk and dispatch read-only investigation vectors

- **Trivial typo** (already isolated to one obvious line) or **single-agent host:** skip straight to **find-it** -> **fix-it**.
- **`low` bug** (narrow scope, single clear repro path, no concurrency, security, persistence, or cross-layer ambiguity): start with **one** blind read-only `astack:reviewer` running **find-it**. Escalate to multiple vectors below if it cannot reproduce cleanly or surfaces competing causes.
- **`risky` or ambiguous bug** (intermittent, multi-layer, concurrent, persistence/auth/security, or unclear root cause): swarm **at least two** blind read-only reviewers from `reviewer_pool`, split across **complementary reproduction and investigation methods** rather than code folders:
  - end-to-end correlated-data and full-environment replay;
  - boundary, state-transition, and concurrency stress;
  - history, config, and environment bisection;
  - runtime profiling, tracing, and telemetry.

Instruct every investigator to follow **find-it** in order—replicate from real data and environment, **shrink the repro first**, then prove the root cause—and return runnable repros, evidence, and minimal fix proposals with **blast-radius**.

## 3. Converge via peer **challenge** (when multiple vectors ran)

1. **Fresh runs, reset timers:** finished reviewers cannot be messaged in place. Spawn fresh read-only reviewers with reset timers (`reviewer_minutes`) and all peer reports so they try to disprove weak theories (**challenge**). If competing fixes need runtime comparison, dispatch workers in isolated workspaces and resubmit those workspaces to the reviewers.
2. **Stop rule (**no-picked-constants**, **decisions-in-plain-words**):**
   - **Converged:** one verified root cause and minimal fix survives. Log every **rejected root-cause theory** and **rejected fix approach** with its disproving evidence as `decided:` in `LANES.md` (`astack-decisions`), then go to Step 4.
   - **No convergence / stalled:** if a round produces no new runnable evidence, hits a genuine product trade-off, or runs out of approved models, stop immediately. Escalate plainly to the person with surviving hypotheses, candidate fixes, **blast-radius**, and your recommendation before any worker edits code.

## 4. Implement via worker (**fix-it**) and resubmit

Dispatch `astack:worker` in an isolated workspace with the converged root cause, shrunk repro, chosen fix, and rejected theories (`decided:`). Require **fix-it** discipline and a report of any **failed fix approaches** (workers never spawn subagents). Resubmit the worker's workspace to the post-fix reviewers.

## 5. Post-fix vectored **review** with **prove-it**

1. Log any worker-reported failed fix approaches as `decided:`.
2. Run vectored **review** (`astack-review-ledger` + `astack-check-gates`), passing the bug dossier, shrunk repro, rejected theories, and failed fix approaches.
3. Require deterministic **prove-it** verification on the real artifact (plus telemetry frequency where relevant) and concise runnable proof.
4. Route any proven gap back to a fresh worker and resubmit to reviewers until clear.
5. Attach the **prove-it** verification summary and runnable evidence to any PR generated for the fix (**watch-pr**).

## 6. Clean up and close with **lookback** + **make-it-stick**

1. Sweep **no-leaked-secrets** on the diff and PR evidence. Run **cleanup** on `<file>_DEBUG_<shorthash>.<type>` captures and scratch workspaces while preserving PR proof.
2. Run **lookback** over the dossier, shrunk repro, rejected theories, failed fix approaches, and final fix to save or update `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md`.
3. Pair with **make-it-stick** for structural guards. Whenever a guard on the fix ladder needs code edits, the lead dispatches a fresh `astack:worker` in an isolated workspace and resubmits it to **review** before landing.
