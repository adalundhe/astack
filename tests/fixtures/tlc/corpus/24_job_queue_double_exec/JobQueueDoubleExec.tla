---- MODULE JobQueueDoubleExec ----
EXTENDS Naturals
VARIABLES runs, acked
Init == runs = 0 /\ acked = FALSE
ExecCrashBeforeAck == runs = 0 /\ runs' = 1 /\ acked' = FALSE
RedeliverExec == runs = 1 /\ acked = FALSE /\ runs' = 2 /\ acked' = FALSE
Stay == runs = 2 /\ UNCHANGED <<runs, acked>>
Next == ExecCrashBeforeAck \/ RedeliverExec \/ Stay
AtMostOnce == runs <= 1
====
