"""Separated offline oracle for `rule-least-privilege`."""
from __future__ import annotations

from pathlib import Path

_FIXED_RBAC = '''from __future__ import annotations

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
        actions=frozenset({"invoices:read"}),
        resources=frozenset({"invoices"}),
        tenant_scoped=True,
    ),
    "invoice_worker": PolicyRule(
        role="invoice_worker",
        actions=frozenset({"invoices:read", "invoices:create"}),
        resources=frozenset({"invoices"}),
        tenant_scoped=True,
    ),
    "migrator": PolicyRule(
        role="migrator",
        actions=frozenset({"schema:migrate"}),
        resources=frozenset({"database"}),
        tenant_scoped=False,
    ),
    "admin": PolicyRule(
        role="admin",
        actions=frozenset({"admin:audit", "invoices:delete", "users:manage"}),
        resources=frozenset({"audit", "invoices", "users"}),
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
        if not identity.roles:
            return False
        for role_name in identity.roles:
            rule = self._policies.get(role_name)
            if rule is None:
                continue
            if action not in rule.actions or resource not in rule.resources:
                continue
            if rule.tenant_scoped:
                if not resource_tenant or resource_tenant != identity.tenant:
                    continue
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
        self._engine.authorize(identity, "invoices:create", "invoices", resource_tenant=owner_tenant)
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
        self._engine.authorize(identity, "invoices:read", "invoices", resource_tenant=owner_tenant)
        if invoice_id not in self._invoices:
            raise KeyError(invoice_id)
        record = self._invoices[invoice_id]
        if record["owner_tenant"] != owner_tenant:
            raise PermissionError("invoice does not belong to requested tenant")
        return dict(record)

    def delete_invoice(
        self,
        identity: Identity,
        invoice_id: str,
        *,
        owner_tenant: str,
    ) -> None:
        self._engine.authorize(identity, "invoices:delete", "invoices", resource_tenant=owner_tenant)
        self._invoices.pop(invoice_id, None)
'''

_FIXED_TESTS = '''import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from rbac import DEFAULT_POLICIES, Identity, InvoiceService, PolicyEngine


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

    def test_policies_contain_no_wildcards(self):
        for role_name, rule in DEFAULT_POLICIES.items():
            for token in set(rule.actions) | set(rule.resources):
                self.assertNotIn("*", token, f"wildcard found on {role_name}")

    def test_non_privileged_reader_allow_and_deny(self):
        engine = PolicyEngine()
        svc = InvoiceService(engine)
        worker = Identity("svc-worker", ("invoice_worker",), "tenant-a")
        reader = Identity("svc-reader", ("invoice_reader",), "tenant-a")
        svc.create_invoice(worker, "inv-3", 900, owner_tenant="tenant-a")

        self.assertEqual(svc.get_invoice(reader, "inv-3", owner_tenant="tenant-a")["amount_cents"], 900)
        with self.assertRaises(PermissionError):
            svc.create_invoice(reader, "inv-4", 100, owner_tenant="tenant-a")
        with self.assertRaises(PermissionError):
            svc.delete_invoice(reader, "inv-3", owner_tenant="tenant-a")
        with self.assertRaises(PermissionError):
            svc.get_invoice(reader, "inv-3", owner_tenant="tenant-b")

    def test_worker_migration_separation_and_no_fallback(self):
        engine = PolicyEngine()
        worker = Identity("svc-worker", ("invoice_worker",), "tenant-a")
        migrator = Identity("ci-migrator", ("migrator",), "platform")
        nobody = Identity("nobody", (), "tenant-a")
        unknown = Identity("ghost", ("unknown_role",), "tenant-a")

        self.assertFalse(engine.is_allowed(worker, "schema:migrate", "database"))
        self.assertFalse(engine.is_allowed(worker, "invoices:delete", "invoices", resource_tenant="tenant-a"))
        self.assertTrue(engine.is_allowed(migrator, "schema:migrate", "database"))
        self.assertFalse(engine.is_allowed(migrator, "invoices:create", "invoices", resource_tenant="tenant-a"))
        self.assertFalse(engine.is_allowed(nobody, "invoices:read", "invoices", resource_tenant="tenant-a"))
        self.assertFalse(engine.is_allowed(unknown, "invoices:read", "invoices", resource_tenant="tenant-a"))


if __name__ == "__main__":
    unittest.main()
'''


def apply(ws: Path) -> dict[str, object]:
    repo = ws / "repo"
    (repo / "src" / "rbac.py").write_text(_FIXED_RBAC, encoding="utf-8")
    (repo / "tests" / "test_rbac.py").write_text(_FIXED_TESTS, encoding="utf-8")
    return {
        "final_text": (
            "Removed wildcard grants and admin fallback from src/rbac.py, scoped every role to its exact "
            "actions/resources with tenant enforcement and runtime-vs-migrator separation, and added allow/deny "
            "tests executed as real non-privileged identities."
        ),
    }
