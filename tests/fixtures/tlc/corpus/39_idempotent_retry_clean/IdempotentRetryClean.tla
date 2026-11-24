---- MODULE IdempotentRetryClean ----
EXTENDS Naturals
VARIABLES sent, applied
Init == sent = 0 /\ applied = 0
SendFirst == sent = 0 /\ sent' = 1 /\ applied' = 1
RetryDedup == sent = 1 /\ applied = 1 /\ sent' = 2 /\ applied' = 1
Done == sent = 2 /\ UNCHANGED <<sent, applied>>
Next == SendFirst \/ RetryDedup \/ Done
AppliedAtMostOnce == applied <= 1
====
