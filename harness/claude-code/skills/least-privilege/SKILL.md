---
name: least-privilege
description: "Scope every identity, token, role, workload, and network policy to the exact actions, resources, conditions, federation claims, and paths required—never wildcards or admin shortcuts—and prove both allow and deny as the real non-privileged identity. Use when writing or reviewing auth, IAM, RBAC, DB grants, KMS/secrets access, API tokens, or firewall/network policies on any platform."
disable-model-invocation: true
---

# Least privilege

Grant every identity, role, token, workload, and network rule only the exact actions, resources, conditions, and paths it requires—never wildcards or admin shortcuts—and prove both what it can and cannot do as the real non-privileged identity.

Apply these principles to whatever cloud, edge, orchestrator, database, or identity provider the repo uses (**analyze-environment**); named tools below are illustrative, never exhaustive.

## Start with

1. **Scope actions, resources, and conditions explicitly:** name exact operations, target resources/scopes, and constraining conditions (source account/project/VPC/IP/service). Never grant wildcards (`*`), root/owner/admin presets, global account keys, or open `0.0.0.0/0` ingress unless explicitly required by a public boundary or documented API limitation.
2. **Lock down trust and federation boundaries:** constrain OIDC, workload identity, cross-account/tenant role assumption, and Zero Trust policies to exact issuer, audience, repo/branch/environment, or workload identity—never wildcard subject (`sub`) claims across orgs, branches, or namespaces (prevents confused-deputy takeover).
3. **Separate runtime, migration, deploy, and admin identities:** serving workloads get minimal runtime data/API rights only; schema migrations, CI/CD deploys, DNS/edge automation, and break-glass administration run under distinct, tighter identities.
4. **Preserve live workloads during revocations (**safe-to-deploy**):** when tightening or rotating live identities, use expand -> switch -> contract so running workloads, scheduled jobs, and rollbacks don't break mid-deploy.
5. **Prove both allow and deny as the real identity (**prove-it**):** verify allowed actions succeed *and* disallowed actions fail using the target non-privileged identity or the platform's policy simulator/troubleshooter (e.g., cloud IAM simulator/troubleshooter, `kubectl auth can-i --as=...`, scoped token verify, non-superuser DB role)—never test only as admin/superuser.

## Watch for

- wildcards, broad built-in owner/editor/admin roles, global API keys, or superuser shortcuts;
- wildcard federation/OIDC subject claims or cross-account trust lacking source constraints;
- `0.0.0.0/0` ingress on private services or broad egress where private connectivity exists;
- encryption-key or secret-store policies scoped to an entire account/project instead of specific workloads;
- default workload identities with broad ambient rights or unnecessary token auto-mounting;
- tests passing only because the runner holds elevated privileges.

**The test:** if this token, role, or workload is compromised, what is the exact blast radius—and did we prove disallowed actions are actually denied?

## When it doesn't fit

- provider APIs that genuinely require a broad read-only resource scope, documented inline with the narrowest condition keys available;
- intentionally public internet ingress, still restricted behind TLS, WAF/rate limits, and private or authenticated origins.

**Showing it:** execute a disallowed action or unauthorized identity assumption as the target identity (or via the platform's policy evaluator) and show it succeeds when it must be denied.

Referenced skills: `analyze-environment` (`${CLAUDE_SKILL_DIR}/../analyze-environment/SKILL.md`), `safe-to-deploy` (`${CLAUDE_SKILL_DIR}/../safe-to-deploy/SKILL.md`), `prove-it` (`${CLAUDE_SKILL_DIR}/../prove-it/SKILL.md`). Read any cited skill file before acting when its trigger applies.
