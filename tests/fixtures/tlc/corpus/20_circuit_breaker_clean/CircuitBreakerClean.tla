---- MODULE CircuitBreakerClean ----
VARIABLE cb
Init == cb = "closed"
Success == cb = "closed" /\ cb' = "closed"
Trip == cb = "closed" /\ cb' = "open"
Cooldown == cb = "open" /\ cb' = "half_open"
ProbeOk == cb = "half_open" /\ cb' = "closed"
ProbeFail == cb = "half_open" /\ cb' = "open"
Next == Success \/ Trip \/ Cooldown \/ ProbeOk \/ ProbeFail
ValidCb == cb \in {"closed", "open", "half_open"}
====
