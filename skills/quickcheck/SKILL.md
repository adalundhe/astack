---
name: quickcheck
description: "Run one focused reviewer for real blockers without vectored review or context-blind noise. Use when the user explicitly requests /astack:quickcheck on worker work, changes, or existing code."
disable-model-invocation: true
---

# Quickcheck

Run a **single focused read-only reviewer** for real blockers instead of full vectored **review**.

## When it applies

- **Pre-ship worker check:** the user invokes `/astack:quickcheck` (or asks for `quickcheck`) in their initial prompt to Lead to check a worker's completed work before shipping.
- **Direct check on any changes or code:** the user invokes `/astack:quickcheck` directly on any branch, diff, PR, files, or existing code.
- **Explicit opt-in only.** Never self-select `quickcheck` to downgrade default vectored **review** when the user did not ask for it.

## Focused reviewer directive

Give the reviewer this exact mandate:

> Find any blockers with respect to known architectural choices and tradeoffs, known issues, or expected tooling or implementation behaviors. Block push and PR creation only on such blocking issues, and do not perform vectored review. Once the worker has fixed these issues, the work may be committed, pushed, and the PR created. Do not raise issues that the user has already clarified, are explained or have solutions clearly documented elsewhere in documentation or in surrounding code, tooling, or environment.

## 1. Gather surrounding context first (**rtfm**, **lookup**, **analyze-environment**)

Cut context-blind false flags before judging code.

1. Scope the check to the worker's branch/diff (pre-ship mode) or whatever branch, diff, PR, or code the user named (defaulting to current branch changes plus uncommitted edits).
2. Read the user's clarifications from the prompt and thread. Read project guides (`README.md`, `AGENTS.md`, `CLAUDE.md`, repo ADRs, docs), git history, and any PR or issue threads (**rtfm**).
3. Consult saved `~/.astack/<project>/` decisions, docs, reviews, and lessons (**lookup**). Check `TOOLS.md` or run read-only environment probes (**analyze-environment**) when tooling or runtime behavior matters.
4. Pass all user clarifications, settled architectural tradeoffs, docs links, and environment facts in the reviewer brief.

## 2. Dispatch one read-only reviewer (no vectored review)

1. Follow **lead** for isolated workspaces (**slates** or a read-only git worktree), role timers, `LANES.md` logging, and cross-harness dispatch (`astack-dispatch`).
2. Dispatch **exactly one** dedicated read-only `astack:reviewer`. Never substitute a generic agent.
3. Choose one approved model from `reviewer_pool`, preferring a non-worker model when available. If `reviewer_pool` is unset or single-model, use the active session model quietly. Never substitute an unapproved model outside `reviewer_pool`.
4. **Skip vectored review.** Do not split the diff into behavioral vectors, run `astack-review-ledger` risk-scaling waves, or dispatch parallel blind reviewers.
5. Allocate a review bundle (`astack-tools reviews path <project> --new --ensure`) and repro folder (`astack-tools repros path <project> --ensure`). Put the resolved absolute `skills/` path (`astack-tools skills-dir`, never `..`) on line 1 of the brief and stamp `Started`, `Wind down at`, and `End by` UTC times.
6. Keep the reviewer strictly read-only. Reviewers never write or apply fixes themselves.

## 3. Reviewer rules: real blockers only, zero noise

1. **Read surrounding docs, code, tooling, and environment first (**rtfm**).** Verify how local tools, build scripts, and documented conventions actually work before flagging anything.
2. **Raise only real blockers (`P0–P2`)** against:
   - known architectural choices and tradeoffs,
   - known issues or regressions, or
   - expected tooling or implementation behaviors.
3. **Suppress context-blind noise.** Never raise issues that:
   - the user has already clarified or accepted,
   - are explained or have documented solutions in docs, ADRs, surrounding code, tooling, or environment, or
   - are style nits, speculative questions, or unproven hunches.
4. **Prove every blocker (**prove-it**).** Save raw evidence or a runnable failing repro in the review bundle or repro folder. Drop any concern you cannot verify locally.
5. Return the standard reviewer report (`VERDICT: CLEAR | BLOCKED`, `BLOCKING (P0–P2)`, `CONFIRMED`, `HELD`, `COULD NOT TEST`), keeping empty sections as `none`.

## 4. Verify blockers, fix once, and ship cleanly

1. Lead inspects the single reviewer's saved evidence and reruns every claimed blocker before keeping it. Discard any item already answered by user clarifications, docs, surrounding code, tooling, or environment.
2. Run `astack-check-gates <base>..<head>` on changed code so deleted or weakened tests never slip past.
3. **When zero verified blockers remain (`CLEAR`):**
   - **Pre-ship worker work:** verify the branch or merge (`astack-verify-merge` when landing), then commit, push, and create the PR without extra review waves.
   - **Direct check on changes or code:** report the clean status, what held, and any `Could not check` gaps.
4. **When verified blockers exist:**
   - Block commit, push, and PR creation **only** on those verified blocking issues.
   - **Pre-ship worker work:** send the proven blockers to the `astack:worker` to fix in its isolated workspace and rerun the failing repros plus touched checks. Once verified fixed and `astack-check-gates` passes, commit, push, and create the PR.
   - **Direct check on changes or code:** report only the verified blockers with repros and concrete fixes, routing fixes to an `astack:worker` only if requested.

## 5. Report plainly and clean up (**wat**, **cleanup**, **no-leaked-secrets**)

1. Lead with the bottom line (**wat**): verified blockers with repros and fixes (or clean clearance), what held, and any `Could not check` items.
2. Never leak internal harness state (model rosters, `reviewer_pool`, `settings.json`, worktree paths, or `[rule: ...]` tags).
3. Clean up scratch workspaces (**cleanup**) and sweep outputs for secrets (**no-leaked-secrets**).
