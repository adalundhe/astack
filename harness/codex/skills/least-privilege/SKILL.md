---
name: least-privilege
description: "Scope every identity, token, role, workload, and network rule to exact actions, resources, conditions, and federation claims—never wildcards or admin shortcuts—and prove both allow and deny as the real non-privileged identity."
---

# Least privilege

Grant every identity, role, token, workload, and network rule only the exact actions, resources, and conditions it requires. Prove both what it can and cannot do as the real non-privileged identity.

Apply this across whatever cloud, edge, orchestrator, database, or identity provider the repo uses (**analyze-environment**); named tools below are illustrative, never exhaustive.

## Start with

1. **Scope actions, resources, and conditions explicitly:** name exact operations, target resources, and constraining conditions (account, project, VPC, IP, service). Never grant wildcards (`*`), root/admin presets, global keys, or `0.0.0.0/0` ingress unless required by a public boundary or documented API limit.
2. **Lock down trust and federation boundaries:** constrain OIDC, workload identity, cross-account roles, and Zero Trust rules to exact issuer, audience, repo, branch, or namespace. Never wildcard subject (`sub`) claims, because wildcards enable confused-deputy takeover.
3. **Separate runtime, migration, deploy, and admin identities:** give serving workloads minimal runtime rights only. Run schema migrations, CI deploys, DNS automation, and break-glass admin under distinct identities.
4. **Preserve live workloads during revocations (**safe-to-deploy**):** tighten or rotate live identities via expand -> switch -> contract so running jobs and rollbacks keep working.
5. **Prove both allow and deny as the real identity (**prove-it**):** verify allowed actions succeed *and* disallowed actions fail using the target non-privileged identity or policy simulator (`kubectl auth can-i --as=...`, IAM simulator, scoped token, non-superuser DB role). Never test only as admin.

## Watch for

- wildcards, owner/editor/admin presets, global API keys, or superuser shortcuts;
- wildcard OIDC subject claims or cross-account trust lacking source constraints;
- `0.0.0.0/0` ingress on private services or broad egress where private paths exist;
- KMS or secret-store policies scoped to a whole account instead of specific workloads;
- default workload identities with ambient rights or unnecessary token auto-mounting;
- tests passing only because the runner holds elevated privileges.

**The test:** if this token, role, or workload is compromised, what is its blast radius—and did we prove disallowed actions fail?

## When it doesn't fit

- provider APIs that genuinely require broad read-only scopes, documented inline with the narrowest condition keys available;
- intentionally public internet ingress, still gated behind TLS, WAF/rate limits, and authenticated origins.

**Showing it:** execute a disallowed action or unauthorized identity assumption as the target identity (or via the policy evaluator) and show it succeeds when it must be denied.

Referenced skills: `analyze-environment` (`../analyze-environment/SKILL.md`), `safe-to-deploy` (`../safe-to-deploy/SKILL.md`), `prove-it` (`../prove-it/SKILL.md`). Read any cited skill file before acting when its trigger applies.
