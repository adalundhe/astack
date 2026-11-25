---
name: adversarial-review
description: "Try to break a change in its real environment, verify coding rules, and report proven blockers first. Use when reviewing a fix, feature, branch, or PR."
disable-model-invocation: true
---

# Adversarial review

Try to break the change the way its users would, in its real environment. Research surrounding context first, enforce coding rules, prove every blocker on rerun, and state defects plainly.

Reviewers never edit code or apply candidate fixes themselves, because authors test what they meant to build. Save standalone failing repro scripts (non-zero on buggy code, `0` once fixed) outside `repo/`. Return findings and recommended fixes to Lead so a worker implements them in an isolated `slates` volume or git worktree.

1. **Research first (**rtfm**).** Read surrounding callers, tests, configs, `RULES.md`, project guides, git history, PR description, all PR comments and review threads, and every linked issue, PR, discussion, ADR, or doc. Follow links instead of guessing.
   - **Never ask drive-by questions** (*"Is X guaranteed?"*, *"Was Y intentional?"*) when code, git log, PR threads, docs, or running it already answer them. Surface an unresolved gap only when nothing settles it, stating what you checked and what decision is needed.
2. **Run it for real (**prove-it**).** Use a local dev environment whenever possible, or an environment explicitly approved in your brief. Never test against production, because adversarial probes can corrupt live data or trigger outages.
3. **Judge in context (**blast-radius**).** Focus on your assigned vector while keeping the whole diff in view. Report any proven bug outside your vector too, naming its root-cause vector. Skip issues already handled by surrounding systems.
4. **Cross-check for contradictions and state them plainly.** Compare code against the PR description, commits, linked issues, ADRs, docs, tests, and PR comments. Name **both sides** of every contradiction and the concrete fix. Never soften a proven defect into a polite question.
   - NOT: `"69a34f1 says tools-useast1-prod was bootstrapped."`
   - YES: `"README.md:42 says tools-useast1-prod is not bootstrapped, but commit 69a34f1 says it was. Update README.md or verify cluster state."`
5. **Reproduce before the change.** Without the change, reproduce every bug it claims to fix from the user's side. If you cannot reproduce a failure, report it as unreproduced rather than fixed.
6. **Verify the change.** With the change applied, rerun each reproduction and verify every acceptance criterion and test. For bug fixes, run **prove-it** on the real artifact using the original bug dossier and return concise before/after proof ready for the PR.
7. **Attack it.** Stress-test the change across every applicable axis, seeding inputs and fault schedules per **full-spectrum-testing**:
   - **Input:** invalid, empty, huge, malformed, oddly encoded, out of order.
   - **Load:** concurrent callers, bursts, sustained overload.
   - **Faults:** slow or failing dependencies, mid-operation restarts, lost or duplicated messages, full disk.
   - **Concurrency:** races, deadlocks, and livelocks around locks, retries, or waits.
   - **Misuse:** plausible mistakes by a user, scripted client, or agent.
   - **Rollout & rollback (**safe-to-deploy**):** for migrations, auth/IAM, infra, or schema/API changes, verify pre-change workloads and rolled-back releases still work.
8. **Enforce astack coding rules.** Open and read the matching rule `SKILL.md` from `skills/` whenever its trigger appears, checking `Watch for`, `Showing it`, and `When it doesn't fit`:
   - Schemas, structs, state, algorithms -> `data-structures-first`
   - Lifecycle flags, order-dependent behavior -> `no-implicit-states`
   - `try`/`except`, retries, fallbacks, silent `None`/defaults -> `no-hidden-flow-control`
   - CLI flags, env vars, config files, toggles -> `no-hidden-config`
   - Caches, duplicated state, denormalized copies -> `minimize-state-stores`
   - Parsing inputs, files, wire formats, DB rows, API replies -> `check-your-boundaries`
   - Locks, threads, processes, shared mutable state -> `no-shared-writes`
   - Migrations, deploys, retries, jobs, idempotency -> `safe-to-rerun`
   - Migrations, auth/identity, infra, DNS/edge, deploy waves, rollback -> **safe-to-deploy**
   - Auth, identities, tokens, roles, RBAC, DB grants, keys, network rules -> `least-privilege`
   - Declarative infra, IaC, edge/DNS/WAF, cluster manifests, stateful stores -> `safe-iac`
   - Network boundaries, retries, timeouts, queues, pools, probes, drain -> `fail-safely`
   - Services, jobs, workers, queues, alerts, telemetry, runbooks -> `observable-by-default`
   - Adding a requirement onto existing code -> `no-bolt-ons`
   - Shims, legacy paths, dead flags, unused code -> `yagni`
   - Comments -> `comment-cop`
   - User-facing CLI, UI, errors, defaults, public APIs -> `delight-users`
   - Magic numbers, timeouts, limits, batch/pool sizes, thresholds -> `no-picked-constants`
   - Sleeps, polling loops, timers, waits -> `event-driven`
   - Optimizations, approximations, deferred shortcuts -> `never-trade-functionality`
   - Secrets, tokens, credentials, PII, logs, errors, debug dumps -> `no-leaked-secrets`
   - Tests, assertions, mocks, tolerances, skips -> `tests-assert-behaviour`
   - Changed behavior, interfaces, config, architecture, or ops (audit repo docs) -> `technical-writing`

   Tag every rule finding with `[rule: <name>]` (internal-only for Lead). Departing from a rule without justification is a real finding even when tests pass.
9. **Prove every finding.** Include runnable steps, actual output, and expected output. Blockers must be proven locally; unproven suspicions never block. Run each repro without the change too to state whether the change caused it, left it, or failed to fix it.
10. **Rank by user impact.** Keep `P0–P5` strictly internal-only for Lead; surface only blockers, suggestions, and nits externally:
    - **P0:** critical outage or whole systems broken.
    - **P1:** widespread breakage or severe degradation on core systems.
    - **P2:** primary feature broken, or limited widespread breakage.
    - **P3:** secondary feature broken or notable non-breaking bug in a primary feature.
    - **P4:** isolated intermittent issue or minor bug in a secondary feature.
    - **P5:** rare, non-breaking nit.

    P0–P2 are blocking, P3 is a suggestion, P4 is a suggestion or nit, and P5 is a nit.

**Reply (internal-only to Lead):** put `VECTOR` and `MODEL` (internal-only for Lead) at the top, followed by blockers, suggestions, nits, and what held. For each finding, include:
- what is wrong (both sides of any contradiction);
- user impact and when it hits;
- exact repro or citation plus runnable evidence;
- recommended fix, internal `[rule: <name>]` tag, and root-cause vector if outside yours.

Referenced skills: `rtfm` (`../rtfm/SKILL.md`), `prove-it` (`../prove-it/SKILL.md`), `blast-radius` (`../blast-radius/SKILL.md`), `full-spectrum-testing` (`../full-spectrum-testing/SKILL.md`), `safe-to-deploy` (`../safe-to-deploy/SKILL.md`). Read any cited skill file before acting when its trigger applies.
