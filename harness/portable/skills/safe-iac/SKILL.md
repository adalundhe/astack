---
name: safe-iac
description: "Audit real infrastructure, edge, and cluster plans/diffs against live state action-by-action for surprise destroys and drift, protect stateful and routing/DNS resources, pin immutable versions/digests, and bound quotas and spend. Use when writing, refactoring, or reviewing any IaC, edge/DNS/WAF config, or cluster manifest."
disable-model-invocation: true
---

# Safe IaC

Never judge infrastructure, edge, or cluster changes from syntax validation or templates alone—inspect the real plan/diff against live state, protect stateful and routing resources from accidental replacement, and bound quotas and spend.

Apply these principles across whatever IaC, GitOps, cloud, edge, or cluster tooling the repo uses (**analyze-environment**); named commands below are illustrative, never exhaustive.

## Start with

1. **Verify active target context first (**analyze-environment**):** confirm the exact target account/project/subscription/zone, region, workspace/stack, and cluster context in `TOOLS.md` before planning or inspecting state.
2. **Audit the real plan or diff action-by-action (**prove-it**):** run the toolchain's read-only preview against live state (e.g., `plan`, `preview`, `what-if`, `diff`, `--dry-run`) and inspect every create, in-place update, and especially every **destroy or replace**. Never assume a small config edit is in-place.
3. **Check live drift before applying:** flag any out-of-band console or incident hotfixes surfaced by the diff; reconcile or import intentional live changes before applying so IaC does not silently revert an active fix.
4. **Protect stateful and critical routing resources:**
   - Guard databases, object stores, queues, encryption keys, volumes, and critical DNS/WAF/edge configs with deletion protection, backups/snapshots, and change guards.
   - Use state-refactoring primitives (move/alias/import blocks) instead of destroy-and-recreate when renaming addresses or restructuring modules.
   - Sequence live cutovers, DNS TTL lowering, and deploy waves via **safe-to-deploy** and **least-privilege**.
5. **Pin immutable versions and isolate state blast radius:** pin providers, modules, charts, runtimes, and container digests (never floating `latest`). Separate state by environment and risk tier (identity/network/data vs. stateless workloads).
6. **Check quotas, addressing, and spend bounds:** set explicit log/backup retention, autoscaler `min`/`max` bounds, and resource/compute limits; check subnet IP capacity, provider quotas, and cross-zone/NAT/egress/ingestion cost amplification before rollout.

## Watch for

- hidden `forces replacement` / destroy-and-recreate actions on stateful stores, keys, networks, identities, or DNS/edge zones;
- module or resource renames lacking state-move/alias mappings;
- uninspected live drift that would undo an emergency production change;
- floating `latest` tags, unpinned modules/providers/charts, or shared prod/non-prod state;
- unbounded log/storage retention, uncapped autoscalers, or chatty cross-zone/NAT/egress paths;
- changes checked only with offline syntax/template validation instead of a real diff against live state.

**The test:** in the real plan/diff against current live state, is every destroy/replace intentional, safe for live workloads, and backed by a tested recovery path?

## When it doesn't fit

- disposable ephemeral sandboxes with no retained state or shared dependencies;
- an intentional replacement explicitly approved by the person with backup, migration, and rollback steps (**decisions-in-plain-words**, **safe-to-deploy**).

**Showing it:** run the platform's real read-only plan/preview/diff against current state and show the unintended replacement, reverted drift, unpinned digest, or unbounded quota/spend resource.

Referenced skills: `analyze-environment` (`../analyze-environment/SKILL.md`), `prove-it` (`../prove-it/SKILL.md`), `safe-to-deploy` (`../safe-to-deploy/SKILL.md`), `least-privilege` (`../least-privilege/SKILL.md`), `decisions-in-plain-words` (`../decisions-in-plain-words/SKILL.md`). Read any cited skill file before acting when its trigger applies.
