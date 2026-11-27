---
type: llm
---

Evaluate the changes in `./repo` and the final summary against `observable-by-default`.

PASS if all of these hold:
- Removes unbounded ID labels (`user_id`, `request_id`, `job_id`, `trace_id`) from metric labels and uses bounded dimensions (`job_type`, `outcome`, `error_type`) instead.
- Propagates `trace_id` (generating one when absent) in structured logs for both succeeded and failed jobs.
- Retries transient failures up to `max_attempts`, routes unrecoverable failures to `self.dlq` (`DeadLetterRecord`), updates `dlq_depth` and `last_success_ts` heartbeat gauges, and eliminates silent failure drops.
- Unit tests verify bounded metric cardinality, correlation ID propagation, transient retry vs DLQ routing, and heartbeat updates and pass.

FAIL otherwise.
