---- MODULE TwoPhaseCommitClean ----
VARIABLES tm, rm1, rm2
Init == tm = "init" /\ rm1 = "working" /\ rm2 = "working"
Prep1 == rm1 = "working" /\ tm = "init" /\ rm1' = "prepared" /\ UNCHANGED <<tm, rm2>>
Prep2 == rm2 = "working" /\ tm = "init" /\ rm2' = "prepared" /\ UNCHANGED <<tm, rm1>>
Commit == tm = "init" /\ rm1 = "prepared" /\ rm2 = "prepared" /\ tm' = "committed" /\ rm1' = "committed" /\ rm2' = "committed"
Abort == tm = "init" /\ tm' = "aborted" /\ rm1' = "aborted" /\ rm2' = "aborted"
Done == tm \in {"committed", "aborted"} /\ UNCHANGED <<tm, rm1, rm2>>
Next == Prep1 \/ Prep2 \/ Commit \/ Abort \/ Done
Consistent == ~((rm1 = "committed" /\ rm2 = "aborted") \/ (rm1 = "aborted" /\ rm2 = "committed"))
====
