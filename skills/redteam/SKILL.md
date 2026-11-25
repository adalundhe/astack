---
name: redteam
description: "Lead-only proactive adversarial attack-fix-rereview loop: run vectored review waves that actively break, disrupt, and limit-test the live system (local dev builds, approved hosted dev/staging, or live harnesses—never production), dispatch workers to fix proven defects (via dagify or treeify when complex), pair freely with clamber for performance, and repeat until stopping conditions hold or review returns no issues."
disable-model-invocation: true
---

# Redteam

Lead-only proactive attack, fix, and re-review loop for an existing codebase or subsystem. Unlike **bugbash** (which solves a reported bug), **redteam** starts with live-adversarial vectored **review**, fixes what it proves, and repeats until stopping conditions hold or no proven issues remain. Pairs freely with **clamber** whenever performance is in scope.

Follow **lead** for isolated workspaces (**slates** or git worktrees), strict read-only reviewer separation (reviewers never write or apply fixes themselves), role timers, watch-and-swap check-ins, and cross-harness "agents as tools" delegation (`astack-dispatch`).

1. **Scope target, live environments, and stopping conditions (**run-it-back**, **lookup**, **rtfm**):**
   - Restate the target subsystem, attack lenses, and exact stopping conditions. If none are given, stop when vectored **review** returns **no remaining proven issues**.
   - Run **lookup** (`~/.astack/*/lessons/*/LESSON.md`, checking related repos on cross-repo work) and **rtfm** (using `astack:researcher` with **how-it-works** and **analyze-environment** when unfamiliar).
   - Record every **approved live-testing target** in `TOOLS.md` and reviewer briefs: local dev builds, containers, approved hosted dev/staging, or live harnesses. **Never attack production, real customer data, or unapproved shared environments.**

## 2. Attack first via live-adversarial vectored **review**

1. Cut the target into risk-classified vectors (adding a `seams` vector via **blast-radius** when sliced). Dispatch blind read-only reviewers from `reviewer_pool` (**review**, **adversarial-review**, `astack-review-ledger`).
2. **Actively break, disrupt, and limit-test the live system—never stop at static reading.** Run real code in approved local dev builds or hosted dev/staging (**test-drive**, **full-spectrum-testing**, **net-trace**). Attack limits directly: hostile inputs, fuzzing, concurrency storms, overload, crash/restart replay (**safe-to-rerun**), injected faults (**fail-safely**), resource exhaustion, and non-privileged auth probes (**least-privilege**). Reviewers stay read-only on source code, clean up temp test state, and save failing repro scripts outside `repo/`.
3. Rerun every blocking finding, merge overlaps only by fix-equivalence, and check **no-leaked-secrets** and **technical-writing** drift.
4. **Check stopping conditions after every wave:**
   - **Done:** no remaining proven issues (or all user stopping conditions met) -> go to Step 5.
   - **Human call / pool run-out:** escalate product trade-offs or `landing_blocked: true` plainly via **decisions-in-plain-words** without leaking internal status.
   - **Stall / oscillation guard:** if consecutive rounds fail to reduce verified issues or re-introduce fixed bugs, stop looping. Log dead ends (`decided:` in `LANES.md`) and escalate the tension with options.

## 3. Dispatch workers to fix (direct, **dagify**, or **treeify**)

1. Log verified issues plainly (user impact, repro or contradiction citation, recommended fix).
2. Scale planning to complexity:
   - **Focused fixes:** dispatch `astack:worker` lanes directly (**fix-it**, **tests-assert-behaviour**) with disjoint paths, failing repros, and prior rejected theories (`astack-decisions`).
   - **Complex fixes:** plan a reviewed graph with **dagify** (or bottom-up waves with **treeify**, or **cross-repo** across repos) and execute via **lead**.

## 4. Pair with **clamber** when performance is in scope, then re-review

1. Follow **work -> robust -> fast**: land correctness, security, and reliability fixes first.
2. When latency, throughput, memory, or variance ($\sigma$) is in scope, run **clamber** (**benchmarking**, **baseline**, **ab-test**). Baseline median and $\sigma$, hill-climb in isolated worker commits, revert regressions, and preserve all functionality (**never-trade-functionality**).
3. **Loop back to Step 2:** resubmit the updated codebase (with all saved failing repros for **prove-it** verification and a `seams` check) to fresh vectored **review** until stopping conditions hold.

## 5. Squish, clean up, run **lookback**, and report

1. Run **squish** when multi-round commits or PRs can be consolidated cleanly (keeping bisectable **clamber** commits when useful).
2. Sweep **no-leaked-secrets** and run **cleanup** on scratch workspaces and debug captures.
3. Run **lookback** into `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md`, paired with **make-it-stick** (worker + **review** for code guards).
4. Report plainly (**wat**, losses first): rounds run, stopping condition met, proven fixes with **prove-it** evidence and SHAs, **clamber** numbers, and any accepted risks or human calls.
