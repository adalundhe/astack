---
type: llm
---

The text is a code review of `repo/retry_client.py` on branch `lane/retry-client` (NO `/astack:go` hint was given in the prompt). The code has:
1. Silent exception swallowing (`except Exception: return None`) that hides transport/caller errors instead of raising or returning a typed error.
2. Fixed polling sleep loop (`time.sleep(POLL_SLEEP_SECONDS)` with arbitrary magic constants `MAX_RETRIES = 7`, `POLL_SLEEP_SECONDS = 3.5`) and returning `None` when retries exhaust without signaling why.

PASS ONLY if ALL of the following hold:
- Identifies the silent `except Exception: return None` swallowing bug with impact and a concrete fix.
- Identifies the arbitrary hardcoded constants (`MAX_RETRIES = 7`, `POLL_SLEEP_SECONDS = 3.5`) and/or fixed `time.sleep` polling loop with a concrete fix.
- Gives clear, actionable recommendations without lazy drive-by questions or leaked internal review-ledger jargon.

FAIL otherwise.
