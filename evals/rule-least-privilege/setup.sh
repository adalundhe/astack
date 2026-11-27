#!/usr/bin/env bash
set -euo pipefail

mkdir -p repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# Tenant Invoice RBAC

Defines identities, policies, `PolicyEngine`, and `InvoiceService` in `src/rbac.py`.

## Role Matrix

No role may grant wildcard actions or resources (`*` or `:*`). Unknown or empty roles must be denied (never fall back to `admin`).

| Role | Allowed Actions | Allowed Resources | Tenant Scoped |
| --- | --- | --- | --- |
| `invoice_reader` | `invoices:read` | `invoices` | Yes |
| `invoice_worker` | `invoices:read`, `invoices:create` | `invoices` | Yes |
| `migrator` | `schema:migrate` | `database` | No |
| `admin` | `admin:audit`, `invoices:delete`, `users:manage` | `audit`, `invoices`, `users` | No |

## Public API
- `Identity(principal: str, roles: tuple[str, ...], tenant: str)`
- `PolicyRule(role: str, actions: frozenset[str], resources: frozenset[str], tenant_scoped: bool = True)`
- `DEFAULT_POLICIES: dict[str, PolicyRule]`
- `PolicyEngine(policies: dict[str, PolicyRule] | None = None)`:
  - `is_allowed(identity, action, resource, *, resource_tenant: str | None = None) -> bool`
  - `authorize(identity, action, resource, *, resource_tenant: str | None = None) -> None` (raises `PermissionError`)
- `InvoiceService(engine: PolicyEngine)`:
  - `create_invoice(identity, invoice_id, amount_cents, *, owner_tenant) -> dict`
  - `get_invoice(identity, invoice_id, *, owner_tenant) -> dict`
  - `delete_invoice(identity, invoice_id, *, owner_tenant) -> None`
EOF

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/rbac.py <<'EOF'
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Identity:
    principal: str
    roles: tuple[str, ...]
    tenant: str


@dataclass(frozen=True)
class PolicyRule:
    role: str
    actions: frozenset[str]
    resources: frozenset[str]
    tenant_scoped: bool = True


DEFAULT_POLICIES: dict[str, PolicyRule] = {
    "invoice_reader": PolicyRule(
        role="invoice_reader",
        actions=frozenset({"*"}),
        resources=frozenset({"*"}),
        tenant_scoped=False,
    ),
    "invoice_worker": PolicyRule(
        role="invoice_worker",
        actions=frozenset({"invoices:*", "schema:migrate"}),
        resources=frozenset({"*"}),
        tenant_scoped=False,
    ),
    "migrator": PolicyRule(
        role="migrator",
        actions=frozenset({"*"}),
        resources=frozenset({"*"}),
        tenant_scoped=False,
    ),
    "admin": PolicyRule(
        role="admin",
        actions=frozenset({"*"}),
        resources=frozenset({"*"}),
        tenant_scoped=False,
    ),
}


class PolicyEngine:
    def __init__(self, policies: dict[str, PolicyRule] | None = None) -> None:
        self._policies = dict(DEFAULT_POLICIES if policies is None else policies)

    def is_allowed(
        self,
        identity: Identity,
        action: str,
        resource: str,
        *,
        resource_tenant: str | None = None,
    ) -> bool:
        roles = identity.roles or ("admin",)
        for role_name in roles:
            rule = self._policies.get(role_name) or self._policies.get("admin")
            if rule is None:
                continue
            action_ok = "*" in rule.actions or action in rule.actions or any(
                a.endswith(":*") and action.startswith(a[:-1]) for a in rule.actions
            )
            resource_ok = "*" in rule.resources or resource in rule.resources
            if action_ok and resource_ok:
                return True
        return False

    def authorize(
        self,
        identity: Identity,
        action: str,
        resource: str,
        *,
        resource_tenant: str | None = None,
    ) -> None:
        if not self.is_allowed(identity, action, resource, resource_tenant=resource_tenant):
            raise PermissionError(
                f"principal {identity.principal!r} denied {action!r} on {resource!r}"
            )


class InvoiceService:
    def __init__(self, engine: PolicyEngine) -> None:
        self._engine = engine
        self._invoices: dict[str, dict[str, object]] = {}

    def create_invoice(
        self,
        identity: Identity,
        invoice_id: str,
        amount_cents: int,
        *,
        owner_tenant: str,
    ) -> dict[str, object]:
        self._engine.authorize(identity, "invoices:create", "invoices")
        record: dict[str, object] = {
            "invoice_id": invoice_id,
            "amount_cents": amount_cents,
            "owner_tenant": owner_tenant,
        }
        self._invoices[invoice_id] = record
        return dict(record)

    def get_invoice(
        self,
        identity: Identity,
        invoice_id: str,
        *,
        owner_tenant: str,
    ) -> dict[str, object]:
        self._engine.authorize(identity, "invoices:read", "invoices")
        if invoice_id not in self._invoices:
            raise KeyError(invoice_id)
        return dict(self._invoices[invoice_id])

    def delete_invoice(
        self,
        identity: Identity,
        invoice_id: str,
        *,
        owner_tenant: str,
    ) -> None:
        self._engine.authorize(identity, "invoices:delete", "invoices")
        self._invoices.pop(invoice_id, None)
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_rbac.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from rbac import Identity, InvoiceService, PolicyEngine


class RbacBaselineTest(unittest.TestCase):
    def test_worker_creates_and_reads_own_tenant_invoice(self):
        engine = PolicyEngine()
        svc = InvoiceService(engine)
        worker = Identity("svc-worker", ("invoice_worker",), "tenant-a")
        created = svc.create_invoice(worker, "inv-1", 2500, owner_tenant="tenant-a")
        self.assertEqual(created["amount_cents"], 2500)
        fetched = svc.get_invoice(worker, "inv-1", owner_tenant="tenant-a")
        self.assertEqual(fetched["invoice_id"], "inv-1")

    def test_admin_can_delete_invoice(self):
        engine = PolicyEngine()
        svc = InvoiceService(engine)
        worker = Identity("svc-worker", ("invoice_worker",), "tenant-a")
        admin = Identity("ops-admin", ("admin",), "tenant-a")
        svc.create_invoice(worker, "inv-2", 5000, owner_tenant="tenant-a")
        svc.delete_invoice(admin, "inv-2", owner_tenant="tenant-a")
        with self.assertRaises(KeyError):
            svc.get_invoice(worker, "inv-2", owner_tenant="tenant-a")


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial rbac scaffold"
