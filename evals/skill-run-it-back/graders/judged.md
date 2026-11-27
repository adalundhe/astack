---
type: llm
---

Evaluate the workspace state and alignment restatement against `run-it-back/SKILL.md`.

PASS if all of these hold:
- Leaves `./repo` completely untouched.
- Restates in concise, checkable lines:
  1. **Goal** (and in-scope deliverable): export a CSV of active invoices (`status == "active"`) with columns `invoice_id,customer,amount_cents,status`.
  2. **Problem**: manual Friday spreadsheet copying by finance analysts introduces voided/archived invoices and delays reconciliation.
  3. **Done when**: user-visible outcome paired with an executable verification command/check proving only active invoices appear with exact CSV columns and unit tests pass.
  4. **Out of scope**: explicitly excludes BOTH PDF export/rendering AND database schema migrations (noting dark-mode styling as unrelated).
  5. **Assumptions**: concrete checkable statements the stakeholder can strike or correct.

FAIL otherwise.
