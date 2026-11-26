---
name: redteam
description: "Lead-only adversarial attack-fix-rereview loop on live dev/staging until no proven issues remain. Use to proactively break, harden, or limit-test a subsystem."
disable-model-invocation: true
---

# Redteam

Lead-only proactive attack, fix, and re-review loop for an existing codebase or subsystem. Unlike `bugbash` (which chases a reported bug), `redteam` starts with live-adversarial **review** and loops until no proven issues remain. Pair freely with **clamber** when performance is in scope.

## Core rules

- **Never attack production**. Target only local dev builds, containers, approved hosted dev/staging, or live harnesses—never production or real customer data.
- **Attack the live system:** actively break, disrupt, and limit-test real code, because static reading misses runtime limits.
- **Stop on stall or oscillation:** if consecutive rounds fail to reduce verified issues or re-introduce fixed bugs, stop looping. Record dead ends (`decided:` in `LANES.md`) and escalate options.
- **Delegate orchestration:** follow **lead** for **slates** (or worktrees), role timers, watch-and-swap check-ins, and cross-harness "agents as tools" (`astack-dispatch`). Reviewers stay strictly read-only and never write or apply fixes themselves.

## 1. Scope target, live targets, and stopping rules

1. Restate the subsystem, attack lenses, and stopping conditions (`run-it-back`). Default stop: vectored **review** returns **no remaining proven issues**.
2. Run **lookup** (`~/.astack/*/lessons/*/LESSON.md`, checking related repos on cross-repo work) and `rtfm`. Dispatch `astack:researcher` (`how-it-works`, `analyze-environment`) when unfamiliar.
3. Record every approved live-testing target in `TOOLS.md` and reviewer briefs before starting.

## 2. Attack first via live-adversarial vectored **review**

1. Slice the target into risk-classified vectors, adding a `seams` vector (`blast-radius`) when split. Dispatch blind read-only reviewers from `reviewer_pool` (`adversarial-review`, `astack-review-ledger`).
2. Run real code in approved local dev builds or hosted dev/staging (`test-drive`, `full-spectrum-testing`, `net-trace`). Probe hostile inputs, fuzzing, concurrency storms, crash replay (`safe-to-rerun`), injected faults (`fail-safely`), resource limits, and auth (`least-privilege`).
3. Reviewers save standalone failing repros under `~/.astack/<project>/repros/` (`astack-tools repros path`) and collected artifacts under `~/.astack/<project>/reviews/<date_time>/` (`astack-tools reviews path`), cleaning temp target state. Rerun every blocking finding, merge by fix-equivalence, and check `no-leaked-secrets` and `technical-writing` drift.
4. Check stopping conditions after every wave:
   - **Done:** no remaining proven issues (or user stop rules met) -> go to Step 5.
   - **Human call / pool run-out:** escalate product trade-offs or `landing_blocked: true` via `decisions-in-plain-words`, hiding internal status.
   - **Stalled / oscillating:** follow the Core rules stop guard.

## 3. Dispatch workers to fix (direct, **dagify**, or **treeify**)

1. Log verified issues plainly: user impact, repro or contradiction citation, and recommended fix.
2. Scale planning to complexity:
   - **Focused fixes:** dispatch `astack:worker` lanes directly (`fix-it`, `tests-assert-behaviour`) with disjoint paths, failing repros, and rejected theories (`astack-decisions`).
   - **Complex fixes:** plan a reviewed graph via **dagify**, bottom-up waves via **treeify**, or `cross-repo` across repos.

## 4. Pair with **clamber** when performance is in scope, then re-review

1. Follow **work -> robust -> fast**: land correctness, security, and reliability fixes first.
2. When latency, throughput, memory, or variance is in scope, run **clamber** under **benchmarking**'s host-quiescence rules. Baseline median and variance, hill-climb in isolated commits, revert regressions, and preserve functionality (`never-trade-functionality`).
3. Loop back to Step 2 after benchmarking finishes, using saved failing repros (`prove-it`) and a `seams` check until stop rules hold.

## 5. Squish, clean up, run **lookback**, and report

1. Run **squish** to consolidate multi-round commits or PRs cleanly, keeping bisectable **clamber** commits when useful.
2. Sweep `no-leaked-secrets` and run `cleanup` on scratch workspaces and debug captures.
3. Run **lookback** into `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md`, paired with `make-it-stick` (worker + **review** for guards).
4. Report plainly (`wat`, losses first): rounds, stop rule, proven fixes with `prove-it` SHAs, **clamber** numbers, and human calls.

**Done when:** stopping conditions hold, `no-leaked-secrets` and `cleanup` pass, **lookback** is saved, and the plain report cites proven SHAs.

Referenced skills: `review` (`${CLAUDE_SKILL_DIR}/../review/SKILL.md`), `clamber` (`${CLAUDE_SKILL_DIR}/../clamber/SKILL.md`), `lead` (`${CLAUDE_SKILL_DIR}/../lead/SKILL.md`), `slates` (`${CLAUDE_SKILL_DIR}/../slates/SKILL.md`), `lookup` (`${CLAUDE_SKILL_DIR}/../lookup/SKILL.md`), `dagify` (`${CLAUDE_SKILL_DIR}/../dagify/SKILL.md`), `treeify` (`${CLAUDE_SKILL_DIR}/../treeify/SKILL.md`), `benchmarking` (`${CLAUDE_SKILL_DIR}/../benchmarking/SKILL.md`), `lookback` (`${CLAUDE_SKILL_DIR}/../lookback/SKILL.md`), `squish` (`${CLAUDE_SKILL_DIR}/../squish/SKILL.md`). Read any cited skill file before acting when its trigger applies.
