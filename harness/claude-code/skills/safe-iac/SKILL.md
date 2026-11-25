---
name: safe-iac
description: "Audit real infrastructure, edge, and cluster plans/diffs against live state action-by-action for surprise destroys and drift, protect stateful and routing/DNS resources, pin immutable versions/digests, and bound quotas and spend."
disable-model-invocation: true
---

# Safe IaC

Never judge infrastructure, edge, or cluster changes from syntax checks alone. Inspect the real plan/diff against live state, protect stateful and routing resources from surprise replacement, and bound quotas and spend.

Apply this across whatever IaC, GitOps, cloud, edge, or cluster tools the repo uses (**analyze-environment**); named commands below are illustrative, never exhaustive.

## Start with

1. **Verify active target context first (**analyze-environment**):** confirm exact account, project/zone, region, workspace/stack, and cluster context in `TOOLS.md` before planning.
2. **Audit the real plan/diff action-by-action (**prove-it**):** run the read-only preview (`plan`, `preview`, `what-if`, `diff`, `--dry-run`) against live state. Inspect every create, update, and especially every **destroy or replace**, because small config edits often trigger full replacement.
3. **Check live drift before applying:** flag any out-of-band console or incident hotfixes in the diff. Reconcile or import intentional live changes first so IaC does not revert an active fix.
4. **Protect stateful and routing resources:**
   - Guard databases, buckets, queues, KMS keys, volumes, and DNS/WAF configs with deletion protection and snapshots.
   - Use state moves/aliases/imports instead of destroy-and-recreate when renaming resources or modules.
   - Sequence live cutovers, DNS TTL lowering, and deploy waves via **safe-to-deploy** and **least-privilege**.
5. **Pin immutable versions and isolate state:** pin providers, modules, charts, runtimes, and container digests—never floating `latest`. Separate state by environment and risk tier.
6. **Bound quotas, addressing, and spend:** set log/backup retention, autoscaler `min`/`max` bounds, and resource limits. Check subnet IP capacity, provider quotas, and NAT/egress cost amplification before rollout.

## Watch for

- hidden `forces replacement` or destroy-and-recreate actions on stateful stores, keys, networks, identities, or DNS zones;
- resource or module renames missing state-move/alias blocks;
- uninspected drift that would undo an emergency live change;
- floating `latest` tags, unpinned providers/charts, or shared prod/dev state;
- unbounded log retention, uncapped autoscalers, or chatty cross-zone/NAT egress;
- changes validated only offline without a real diff against live state.

**The test:** in the real plan/diff against live state, is every destroy/replace intentional, safe for live workloads, and backed by a tested recovery path?

## When it doesn't fit

- disposable ephemeral sandboxes with no retained state or shared dependencies;
- an intentional replacement approved by the person with backup, migration, and rollback steps (**decisions-in-plain-words**, **safe-to-deploy**).

**Showing it:** run the real read-only plan/diff against live state and show the unintended replacement, reverted drift, unpinned digest, or unbounded resource.

Referenced skills: `analyze-environment` (`${CLAUDE_SKILL_DIR}/../analyze-environment/SKILL.md`), `prove-it` (`${CLAUDE_SKILL_DIR}/../prove-it/SKILL.md`), `safe-to-deploy` (`${CLAUDE_SKILL_DIR}/../safe-to-deploy/SKILL.md`), `least-privilege` (`${CLAUDE_SKILL_DIR}/../least-privilege/SKILL.md`), `decisions-in-plain-words` (`${CLAUDE_SKILL_DIR}/../decisions-in-plain-words/SKILL.md`). Read any cited skill file before acting when its trigger applies.
