---
name: adversarial-review
description: "Review a change by reproducing the original bug, confirming acceptance criteria, trying to break it in its real environment, checking coding rules, and reporting proven blockers first. Use when reviewing a fix, feature, branch, or PR."
---

# Adversarial review

Review a change by trying to break it the way its users would, in its real environment—after researching all surrounding and linked context, enforcing astack's engineering disciplines and coding rules, and stating every defect or contradiction plainly.

1. **Research first — inspect ALL repo, PR, and linked context (**rtfm**).** Before forming findings or questions, read the surrounding codebase (callers, callees, sibling modules, tests, configs, `README`, `RULES.md`, `AGENTS.md`/`CLAUDE.md`/`CONTRIBUTING.md`, docs, ADRs), git history (`git log`, `git blame`), PR description, **all PR comments and inline review threads** (open and resolved), commit messages, and **every linked issue, PR, discussion, ADR, RFC, or doc**. Follow references instead of guessing or asking what they say.
   - **Never ask drive-by questions** (e.g., *"Is X guaranteed?"*, *"Was Y intentional?"*, *"Confirm whether Z is expected"*, *"Can you clarify...?"*). Look up the answer in the repo, git history, PR/issue threads, linked docs, or by running the code. Only surface an unresolved gap if nothing available settles it—and state plainly what you checked, what conflicts, and what decision is needed.
2. **Run it for real (**prove-it**).** Use a local development environment whenever possible, or an environment the person explicitly approved. Never test against production or unapproved systems.
3. **Judge it in context (attack through your assigned vector without blinders).** Learn how the code runs in production and what surrounds it (**blast-radius**). When assigned a review vector (lens, slice, or `seams`), focus your attack there while keeping the full change in view; report any proven bug you uncover even outside your vector, naming the vector where its root cause lives. Don't raise issues already handled by surrounding systems, upstream layers, or documented operational practices.
4. **Cross-check for contradictions and state them plainly.** Explicitly compare:
   - code vs. PR description, commit messages, linked issues, ADRs, READMEs, docs, and inline comments;
   - code vs. tests (weakened assertions, skipped/deleted tests, mock-only theater, or tests contradicting stated intent);
   - author claims in PR comments/discussions vs. actual runtime behavior;
   - one part of the diff vs. another part or surrounding callers/invariants.
   - **Always name BOTH sides of a contradiction and the concrete action in plain English** (**wat**)—never drop cryptic isolated fragments (e.g., NOT `"69a34f1 says tools-useast1-prod was bootstrapped"`; YES: `"The README says tools-useast1-prod is not bootstrapped, but commit 69a34f1 says it was. Update README.md:42 or verify the cluster state so they match."`). Never wrap a proven bug, rule violation, or contradiction in a hedged question.
5. **Reproduce before the change.** Without the change, reproduce every bug it claims to fix from the user's side. If you can't reproduce a failure, report it as unreproduced rather than fixed.
6. **Verify the change.** With the change applied, rerun each reproduction and verify every acceptance criterion and test it claims. Report anything missing or partial.
7. **Attack it.** Stress-test the change from the user's side across every category that applies:
   - **Input:** invalid, empty, huge, malformed, oddly encoded, out of order.
   - **Load:** concurrent callers, bursts, sustained overload.
   - **Faults:** slow or failing dependencies, mid-operation restarts, lost or duplicated messages, full disk.
   - **Concurrency:** races, deadlocks, and livelocks wherever locks, retries, or waits exist.
   - **Misuse:** plausible mistakes by a confused user, scripted client, or another agent.

   Seed generated inputs and fault schedules as in **full-spectrum-testing**.
8. **Enforce astack disciplines and coding rules (open and read every matching rule!).** Never skip rule checks or review from generic habit alone. Check core disciplines (**work -> robust -> fast**, **prove-it**, **blast-radius**, **simplify-me**, **challenge**, **tests-assert-behaviour**, **never-trade-functionality**) AND read the matching coding-rule `SKILL.md` file from the astack `skills/` directory whenever its trigger appears in the diff, verifying its `Watch for` list, `Showing it` check, and `When it doesn't fit` exceptions:
   - Schemas, structs, state, algorithms -> **data-structures-first**
   - Lifecycle flags, order-dependent behavior -> **no-implicit-states**
   - `try`/`except`, retries, fallbacks, silent `None`/defaults -> **no-hidden-flow-control**
   - CLI flags, env vars, config files, toggles -> **no-hidden-config**
   - Caches, duplicated state, denormalized copies -> **minimize-state-stores**
   - Parsing requests, files, wire formats, DB rows, API replies -> **check-your-boundaries**
   - Locks, threads, processes, shared mutable state -> **no-shared-writes**
   - Migrations, deploys, retries, jobs, idempotency -> **safe-to-rerun**
   - Adding a requirement onto existing code -> **no-bolt-ons**
   - Shims, legacy paths, dead flags, unused code -> **yagni**
   - Comments (redundant, stale, misleading) -> **comment-cop**
   - User-facing CLI, UI, errors, defaults, public APIs -> **delight-users**
   - Magic numbers, timeouts, limits, batch/pool sizes, thresholds -> **no-picked-constants**
   - Sleeps, polling loops, timers, waits -> **event-driven**
   - Optimizations, approximations, deferred/cached shortcuts -> **never-trade-functionality**
   - Secrets, tokens, credentials, PII, logs, errors, telemetry, debug dumps -> **no-leaked-secrets**
   - Tests, assertions, mocks, tolerances, skips -> **tests-assert-behaviour**

   Violating the person's explicit rules, or departing from a coding rule's defaults without justification, is a real finding even when tests pass—cite `[rule: <name>]` on every rule finding.
9. **Prove every finding.** Include a runnable reproduction: steps or command, actual output, and expected output. Blockers must be proven locally; unproven suspicions go under unproven and never block. Run each reproduction without the change too, and state whether the change caused it, left it in place, or failed to fix it. For a rule violation or contradiction, prove it using the rule's `Showing it` check or cite the exact conflicting files/lines/commits/comments.
10. **Rank internally by user impact:**
    - **P0:** critical outage or multiple/whole systems broken.
    - **P1:** widespread breakage or severe degradation across common features or a core system.
    - **P2:** primary feature broken, or inconsistent/limited widespread breakage.
    - **P3:** isolated secondary feature broken, notable single-feature degradation, or notable non-breaking bug in a primary feature.
    - **P4:** isolated intermittent issue, moderate degradation, or minor non-breaking bug in a secondary feature.
    - **P5:** rare, non-breaking nit.

    P0–P2 are blocking, P3 is a suggestion, P4 is a suggestion or nit, and P5 is a nit. Keep the P0–P5 labels internal; don't print them in the report.
11. **Report clearly.** State your assigned `VECTOR` and `MODEL` at the top of the report. Lead with blockers, then suggestions, then nits. Every finding must state plainly—never leaving the reader guessing—**(1) what the issue is** (naming both sides for any contradiction, never a cryptic fragment or hedged question), **(2) what the impact is**, **(3) who/when/how often it hits or a concrete example scenario**, **(4) how to reproduce or verify it** (exact command/input/citations and brief evidence), and **(5) the recommended fix** (what to change and where; for a rule departure, cite `[rule: <name>]` and the rule's `Start with` guidance or the evidence needed to justify keeping it; note the root-cause vector if outside your assigned vector). Finish with what you tested that held. Don't edit the code under review; save each blocking reproduction as a standalone runnable script (or `unittest` file) in the designated reproduction folder (e.g., `program/repros/`) that **exits non-zero on the buggy code and exits 0 once the bug is fixed**.

Referenced skills: `rtfm` (`../rtfm/SKILL.md`), `prove-it` (`../prove-it/SKILL.md`), `blast-radius` (`../blast-radius/SKILL.md`), `wat` (`../wat/SKILL.md`), `full-spectrum-testing` (`../full-spectrum-testing/SKILL.md`), `simplify-me` (`../simplify-me/SKILL.md`), `challenge` (`../challenge/SKILL.md`), `tests-assert-behaviour` (`../tests-assert-behaviour/SKILL.md`), `never-trade-functionality` (`../never-trade-functionality/SKILL.md`), `data-structures-first` (`../data-structures-first/SKILL.md`), `no-implicit-states` (`../no-implicit-states/SKILL.md`), `no-hidden-flow-control` (`../no-hidden-flow-control/SKILL.md`), `no-hidden-config` (`../no-hidden-config/SKILL.md`), `minimize-state-stores` (`../minimize-state-stores/SKILL.md`), `check-your-boundaries` (`../check-your-boundaries/SKILL.md`), `no-shared-writes` (`../no-shared-writes/SKILL.md`), `safe-to-rerun` (`../safe-to-rerun/SKILL.md`), `no-bolt-ons` (`../no-bolt-ons/SKILL.md`), `yagni` (`../yagni/SKILL.md`), `comment-cop` (`../comment-cop/SKILL.md`), `delight-users` (`../delight-users/SKILL.md`), `no-picked-constants` (`../no-picked-constants/SKILL.md`), `event-driven` (`../event-driven/SKILL.md`), `no-leaked-secrets` (`../no-leaked-secrets/SKILL.md`). Read any cited skill file before acting when its trigger applies.
