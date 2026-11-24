---- MODULE TwoPhaseCommitSplitBrain ----
VARIABLES rm1, rm2
Init == rm1 = "working" /\ rm2 = "working"
Prep1 == rm1 = "working" /\ rm1' = "prepared" /\ UNCHANGED rm2
EarlyCommit1 == rm1 = "prepared" /\ rm1' = "committed" /\ UNCHANGED rm2
Abort2 == rm1 = "committed" /\ rm2 = "working" /\ rm2' = "aborted" /\ UNCHANGED rm1
Stay == rm2 = "aborted" /\ UNCHANGED <<rm1, rm2>>
Next == Prep1 \/ EarlyCommit1 \/ Abort2 \/ Stay
ConsistentDecision == ~(rm1 = "committed" /\ rm2 = "aborted")
====
