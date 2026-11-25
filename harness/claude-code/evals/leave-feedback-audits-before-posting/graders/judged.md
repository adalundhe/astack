---
type: llm
---

The text is the finalized, human-ready GitHub PR review comment for PR #87 (`lane/webhook-batching`), rewritten from a terrible draft (`program/draft-comment.md`) after checking `repo/` and `program/` context (`pr.md`, `pr-comments.md`, `linked-issue-42.md`, `docs/AD-003.md`, `README.md`, `infra/clusters.json`, git log).

PASS ONLY if ALL of the following hold:
1. **Fixes the cryptic SHA fragment:** clearly states BOTH sides of the contradiction in plain English (that `README.md` says `tools-useast1-prod` is not bootstrapped, while the repo's commit / `infra/clusters.json` says it is bootstrapped) AND gives a concrete action (update `README.md` or verify cluster state). Does NOT leave an unintelligible isolated commit hash statement like `<sha> says tools-useast1-prod was bootstrapped`.
2. **Fixes the vague/inactionable error-handling comment with full 5-part clarity:** plainly states (a) what the issue is (`deliver_batch` in `src/webhooks.py` catches `except Exception: return None`), (b) its impact (failed webhook deliveries are silently dropped in direct contradiction of PR #87 / issue #42 so callers never receive `WebhookDeliveryError`), (c) when/an example scenario + how to reproduce it (e.g., transport returns HTTP 500/502 or raises an exception and `deliver_batch` returns `None` instead of `WebhookDeliveryError`), and (d) a concrete recommended fix (remove the catch-all / let `WebhookDeliveryError` propagate).
3. **Fixes the hardcoded constants comment into a concrete, actionable point:** cites `MAX_BATCH_SIZE = 37` and `TIMEOUT_SEC = 13` contradicting `docs/AD-003.md` and specifies a concrete fix (accept them via constructor/config or derive from payload/SLA budget).
4. **Drops BOTH lazy already-answered questions:** does NOT ask why `/v1/hooks` is read-only (already answered in `docs/AD-003.md`, issue #42, and `pr-comments.md`) and does NOT ask why `Retry-After` is used instead of exponential backoff (already answered in `pr-comments.md`).
5. **Clean, concise, human-ready prose with ZERO leaked internal thinking:** removes `coverage-map.md`, `POOL EXHAUSTED`, `jackknife`, `sonnet/haiku`, `P2`, stilted/rambling filler ("reliability posture", "warrant further consideration"), and internal orchestration narration.

FAIL otherwise.
