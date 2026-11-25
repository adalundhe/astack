---
name: unland
description: "Verify how a change landed and deployed, pick the exact revert/rollback path, and stop on unknown ranges. Use to safely revert or roll back a landed change."
disable-model-invocation: true
---

# Unland

Revert a landed change and roll back its deployment by checking how it actually landed in git and how it deployed. Never guess a commit range or run a generic revert blindly.

**Honest limit:** this skill is a workflow guardrail, not technical enforcement. Honor `settings.json` `autonomy.deny` (`prod_deploy_or_destructive_migration`, `push_protected_branch`, `merge_pr`). Get explicit human approval before touching production or protected branches (`decisions-in-plain-words`).

## 1. Verify how the change landed in git

Inspect target-branch history (`git log --first-parent`, `git show --stat`, `git cat-file -p <sha>`). Also check PR metadata and `<program>/release.json` (`astack-release rollback-plan`) before touching git:

- **Merge commit (2+ parents):** confirm parent 1 is the mainline branch. Revert with `git revert -m 1 <merge_sha>`.
- **Squash merge (1 parent on mainline, different SHA from PR head):** revert the mainline squash SHA (`git revert <mainline_sha>`). Never target the PR `head_sha`, because it is not on mainline.
- **Rebase or fast-forward merge (multiple mainline commits):** prove the exact contiguous mainline range `<oldest>^..<newest>` from history. Revert in reverse order (`git revert --no-commit <oldest>^..<newest>`).
- **Unknown or ambiguous range:** **stop immediately and escalate.** Never guess start/end SHAs or revert a partial slice.
- **Cherry-picks or release branches:** trace every branch carrying the change (`blast-radius`). Plan one revert per branch.

## 2. Verify how it deployed and what state moved

Inspect active contexts (`analyze-environment`, `TOOLS.md`), CI/CD pipelines, and GitOps controllers. Check runtime revisions, CDN/edge/DNS/WAF configs, IaC state, IAM policies, and DB or queue migrations:

- **Mitigate first if degraded (`triage`):** roll back the live artifact revision, traffic split, or feature flag first. Then land the git revert so CI or GitOps does not re-deploy the bad change.
- **Keep rollback order reverse-topological:** roll back downstream callers before upstream schemas, roles, or infra (`astack-release rollback-plan`, `cross-repo`).
- **Protect irreversible state (`safe-to-deploy`, `safe-iac`):** stop and escalate before running destructive down-migrations, resource destroys, or IAM revocations. For IaC rollbacks, save and inspect `plan -out=<file>`, then apply only that plan.

## 3. Execute, verify recovery, and capture the lesson

1. **Revert via branch and PR** (`watch-pr`) unless incident authority permits direct rollback. Never `git push --force` to erase commits on shared or protected branches.
2. **Verify recovery (`prove-it`, `observable-by-default`):** confirm the bad commit or revision is gone. Verify live error rates, probes, and GitOps/CI convergence.
3. **Update tracking and record the lesson:** mark rolled-back release steps (`astack-release mark-rolled-back`) and run `cleanup`. Record findings via **lookback** into `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md` with `make-it-stick`.

**Done when:** landing and deploy methods were verified (or stopped on an unknown range), rollback ran in reverse order, live health and CD convergence pass (`prove-it`), and **lookback** recorded the lesson.

Referenced skills: `lookback` (`../lookback/SKILL.md`). Read any cited skill file before acting when its trigger applies.
