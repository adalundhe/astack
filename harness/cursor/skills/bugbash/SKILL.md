---
name: bugbash
description: "Lead-only multi-reviewer bug investigation and fix workflow: gather all bug/linked context, dispatch a read-only reviewer swarm using find-it across multiple angles, run peer challenge to convergence logging rejected theories (decided:), dispatch workers with fix-it in isolated workspaces, pass original bug docs plus rejected theories and failed fix attempts to post-fix reviewers instructed to use prove-it and attach PR proof, and capture durable lessons via make-it-stick. Use when the lead investigates a complex, subtle, or high-impact bug."
disable-model-invocation: true
---

# Bugbash

Lead-only workflow: swarm read-only reviewers before writing fix code, converge via peer **challenge**, implement cleanly with **fix-it**, verify with **prove-it**, and capture lessons via **make-it-stick**.

- **Watch & swap (all phases, per **lead**):** enforce `settings.json` clocks (`reviewer_minutes`, `worker_minutes`, `wind_down_minutes`, `check_in_minutes`) on every reviewer and worker. Stamp UTC `Started / Wind down at / End by` into briefs (pass `--settings`/`--timeout` to `astack-dispatch run`), log starts in `LANES.md`, check `astack-status` every `check_in_minutes`, remind at wind-down, and stop/swap overdue runs with a fresh successor carrying harvested artifacts/branch SHA and reset timers.
- **Isolated workspaces:** workers implement in **slates** in-memory VFS volumes (`https://github.com/hyper-light/slates`, preferred when available) or git worktrees; reviewers test candidate fixes only in **slates** volumes or throwaway scratch worktrees—never editing the repo under review.

1. **Gather the bug dossier (**rtfm**):** read the report and fetch every linked issue, PR, doc, commit, log, trace, metric, or screenshot. Reuse this dossier for **both** investigation and post-fix review.
2. **Swarm read-only reviewers across angles:** dispatch blind `astack-reviewer` runs (or `astack-dispatch run --role reviewer` from `reviewer_pool`) across complementary vectors (failing path & callers, state/concurrency, protocol/input boundaries, recent regressions) with the full dossier. Instruct each reviewer to:
   - follow **find-it** in order—replicate from real correlated data and full environment conditions, **shrink the repro first**, then narrow and prove root causes—without editing the repo under review;
   - propose minimal fix approaches with trade-offs and **blast-radius**, validating candidates only in a throwaway scratch volume/worktree.
3. **Peer **challenge** with fresh runs and a stop rule:**
   - **Fresh runs, reset timers:** finished reviewers (especially one-shot `astack-dispatch` runs) cannot be messaged in place. Spawn fresh read-only reviewer runs per round with all peer reports (shrunk repros, evidence, diagnoses, fix options) and reset timers (`reviewer_minutes`, logged in `LANES.md`), instructing them to use **challenge** and test competing fixes only in throwaway scratch volumes/worktrees.
   - **Stop rule (**no-picked-constants**, **decisions-in-plain-words**):**
     - **Converged:** competing hypotheses are disproved or conceded with runnable proof, leaving one verified root cause and minimal fix. Log every **rejected root-cause theory** and **rejected fix approach** (with disproving evidence) as `decided:` entries in `LANES.md` (`astack-decisions`), then go to Step 4.
     - **No convergence / stalled:** if a round produces **no new runnable evidence**, hits a genuine product/architectural trade-off, or exhausts approved models/budgets, **stop immediately**. Escalate to the person in plain language with each surviving hypothesis (evidence + gaps), candidate fixes with **blast-radius**, and the lead's recommendation before any worker edits code.
4. **Implement via worker (**fix-it**):** dispatch `astack-worker` (or `astack-dispatch run --role worker`) in an isolated **slates** volume or git worktree with the converged root cause, shrunk repro, chosen fix, and **rejected theories (`decided:` entries)**. Require **fix-it** discipline and a report of any **failed fix approaches/attempts** (workers never spawn subagents).
5. **Post-fix vectored **review** with **prove-it**:** log worker-reported failed fix approaches/attempts as `decided:` entries, then run vectored **review** (`astack-review-ledger` + `astack-check-gates`):
   - Pass post-fix reviewers the **original bug dossier, shrunk repro, rejected theories (`decided:` entries), and failed fix approaches/attempts**.
   - Instruct them to apply **prove-it** (deterministic before/after verification on the real artifact, empirical frequency from telemetry/analytics where relevant) and return concise runnable proof.
   - Route proven gaps back to a fresh worker to strengthen existing tests first and fix cleanly.
   - **Attach proof to the PR:** summarize and attach the **prove-it** verification and runnable evidence (commands, outputs, traces, screenshots, benchmarks) to any PR generated for the fix (**watch-pr**).
6. **Sweep and clean up:** check **no-leaked-secrets** on diff and PR evidence; run **cleanup** to delete `<file>_DEBUG_<shorthash>.<type>` captures and scratch volumes/worktrees while preserving final PR evidence.
7. **Capture lessons (**make-it-stick**):** once post-fix review clears, run **make-it-stick** over the final fix, rejected root-cause theories (`decided:` entries), and failed fix approaches/attempts—recording scoped lessons in `LESSONS.md` and applying the structural fix ladder so the bug class and dead-end traps don't recur.

Referenced skills: `challenge` (`../challenge/SKILL.md`), `fix-it` (`../fix-it/SKILL.md`), `prove-it` (`../prove-it/SKILL.md`), `make-it-stick` (`../make-it-stick/SKILL.md`), `lead` (`../astack-lead/SKILL.md`), `slates` (`../slates/SKILL.md`), `rtfm` (`../rtfm/SKILL.md`), `find-it` (`../find-it/SKILL.md`), `blast-radius` (`../blast-radius/SKILL.md`), `no-picked-constants` (`../no-picked-constants/SKILL.md`), `decisions-in-plain-words` (`../decisions-in-plain-words/SKILL.md`), `review` (`../astack-review/SKILL.md`), `watch-pr` (`../watch-pr/SKILL.md`), `no-leaked-secrets` (`../no-leaked-secrets/SKILL.md`), `cleanup` (`../cleanup/SKILL.md`). Read any cited skill file before acting when its trigger applies.
