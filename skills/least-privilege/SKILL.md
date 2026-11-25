---
name: least-privilege
description: "Scope identities, roles, tokens, and network rules strictly, and prove allow and deny as the real identity. Use when writing or reviewing IAM, RBAC, tokens, policies, or firewall rules."
disable-model-invocation: true
---

# Least privilege

Grant every identity, role, token, workload, and network rule only the exact actions, resources, and conditions it requires. Prove both what it can and cannot do as the real non-privileged identity.

Apply this across whatever cloud, edge, orchestrator, database, or identity provider the repo uses (`analyze-environment`). Named tools below are illustrative, never exhaustive.

## Start with

1. **Scope actions, resources, and conditions explicitly:** name exact operations, resources, and conditions (account, project, VPC, IP, service). Never grant wildcards (`*`), admin presets, global keys, or `0.0.0.0/0` ingress without a documented boundary need.
2. **Lock down trust and federation boundaries:** constrain OIDC, workload identity, and cross-account trust to exact issuer, audience, **and** subject claim (`sub`: exact repo/branch/environment or namespace/service-account). Never allow audience-only trust or wildcard `sub` claims, because either enables confused-deputy takeover.
3. **Separate runtime, migration, deploy, and admin identities:** give serving workloads minimal runtime rights only. Keep migrations, CI deploys, DNS, and admin separate, because mixing them turns any app bug into full compromise.
4. **Preserve live workloads during revocations (`safe-to-deploy`):** tighten or rotate live identities via expand -> switch -> contract so running jobs and rollbacks keep working.
5. **Prove both allow and deny (`prove-it`):** verify allowed actions succeed and disallowed actions fail as the target identity. Use the real scoped token, non-superuser role, `kubectl auth can-i --as=...`, or IAM simulator. Never test only as admin, because elevated runners mask missing or overly broad grants.

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

**Showing it:** run a disallowed action or identity assumption as the target identity (or policy evaluator). Show it succeeds when it must be denied.
