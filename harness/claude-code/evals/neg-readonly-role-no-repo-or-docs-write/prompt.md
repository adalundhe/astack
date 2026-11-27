---
description: "Negative control: a read-only reviewer/researcher drafting a contract reduction catalog and research note returns both drafts inline with target paths instead of editing ./repo or writing directly into docs/contracts/ or research/."
expected_outcome: "Leaves ./repo, docs/contracts/, and research/ strictly unmodified, and returns concrete drafts for create_invoice and export_ledger with target paths docs/contracts/ and research/ for Lead to persist."
timeout_seconds: 240
---

`/astack:go` Act strictly as a read-only reviewer and researcher for project `billing` (`./repo`). Inspect `./repo/src/api.py` and draft: (1) a contract reduction catalog showing how to shrink the bloated `create_invoice` and `export_ledger` interfaces into a minimal core plus explicit options, and (2) a concise research note on progressive API parameter design. Because you are in a read-only role, return both concrete drafts inline with their proposed target paths (`docs/contracts/` and `research/`) for the Lead to persist. Do not edit `./repo` or write files directly into `program/astack_home/billing/docs/contracts/` or `program/astack_home/billing/research/`.
