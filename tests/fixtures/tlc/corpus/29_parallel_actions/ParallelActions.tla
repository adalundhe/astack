---- MODULE ParallelActions ----
VARIABLE phase
Init == phase = "start"
FastPath == phase = "start" /\ phase' = "done"
FallbackPath == phase = "start" /\ phase' = "done"
Heartbeat == phase = "start" /\ phase' = "start"
Stay == phase = "done" /\ phase' = "done"
Next == FastPath \/ FallbackPath \/ Heartbeat \/ Stay
ValidPhase == phase \in {"start", "done"}
====
