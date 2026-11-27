---
type: llm
---

Evaluate the published `AD_2.md` against `create-adc` and `AD_FORMAT.md`.

PASS if all of these hold:
- Publishes `AD_2.md` at `program/astack_home/payments/architecture/AD_2.md` without overwriting `AD_1.md`, without leaving `AD_2.draft.md`, and without writing anything inside `./repo`.
- Frontmatter includes `ad_number: 2`, a clear `name`, and a one-sentence `description`.
- Includes all required sections (`Status` with `Accepted (YYYY-MM-DD)`, `Context`, `Decision`, `Non-goals`, `Costs accepted`, `Alternatives considered`, `Acceptance criteria`, `Tests`, `Evidence`) grounded in the concrete numbers, code paths (`repo/src/ledger.py`), and rejected alternatives (Redis `SETNX`, client sequence numbers) from `program/decision-brief.md`.

FAIL otherwise.
