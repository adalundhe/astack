---
type: llm
---

Evaluate the architecture decision, contract-reduction catalog, progressive SDK refactor, error messages, and documentation sync for `sdk-v2`.

PASS if all of these hold:
- Preserves `program/astack_home/sdk-v2/architecture/AD_1.md` untouched and publishes `AD_2.md` with valid frontmatter (`ad_number: 2`), all 9 required `AD_FORMAT.md` sections, and no leftover draft or in-repo AD files.
- Publishes a contract-reduction catalog under `program/astack_home/sdk-v2/docs/contracts/` citing `client.py:<line>`, auditing redundant/dead parameters, defining progressive tiers, and outlining migration steps.
- Refactors `./repo/src/client.py` so Tier 0 `fetch(url)` works with sensible defaults, Tier 1 (`timeout`, `headers`) and Tier 2 (`retry`/`RetryPolicy`, `transport`) compose optionally, and actionable error messages replace `"ERR_9"` and `"ERR_4"`.
- Syncs `./repo/docs/api.md` with `DEFAULT_TIMEOUT_SECONDS` and the simplified signature, expands `./repo/tests/test_client.py` to catch ceremony and `"ERR_9"` regressions, and preserves gates.

FAIL otherwise.
