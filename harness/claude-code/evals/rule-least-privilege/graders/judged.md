---
type: llm
---

Evaluate the changes in `./repo` and the final summary against `least-privilege`.

PASS if all of these hold:
- Wildcard actions/resources (`*`, `:*`) are removed from `DEFAULT_POLICIES`, and every role grants only the exact documented actions and resources.
- Runtime (`invoice_reader`, `invoice_worker`), migration (`migrator`), and `admin` roles are strictly separated, and empty or unknown roles deny by default with no admin fallback.
- Tenant boundaries are enforced on tenant-scoped operations (`InvoiceService` passes `resource_tenant` and denies cross-tenant access).
- Unit tests prove both allow and deny behavior using real non-privileged identities and pass.

FAIL otherwise.
