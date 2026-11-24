---- MODULE JobQueueClean ----
VARIABLE st
Init == st = "queued"
Claim == st = "queued" /\ st' = "running"
Ack == st = "running" /\ st' = "succeeded"
TransientErr == st = "running" /\ st' = "retrying"
Retry == st = "retrying" /\ st' = "running"
Exhaust == st = "retrying" /\ st' = "dlq"
Terminal == st \in {"succeeded", "dlq"} /\ st' = st
Next == Claim \/ Ack \/ TransientErr \/ Retry \/ Exhaust \/ Terminal
ValidJob == st \in {"queued", "running", "retrying", "succeeded", "dlq"}
====
