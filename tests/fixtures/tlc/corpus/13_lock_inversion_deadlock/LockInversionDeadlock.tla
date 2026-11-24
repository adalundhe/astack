---- MODULE LockInversionDeadlock ----
VARIABLES l1, l2
Init == l1 = "free" /\ l2 = "free"
T1TakeL1 == l1 = "free" /\ l1' = "t1" /\ UNCHANGED l2
T1TakeL2 == l1 = "t1" /\ l2 = "free" /\ l1' = "free" /\ l2' = "free"
T2TakeL2 == l2 = "free" /\ l2' = "t2" /\ UNCHANGED l1
T2TakeL1 == l2 = "t2" /\ l1 = "free" /\ l1' = "free" /\ l2' = "free"
Next == T1TakeL1 \/ T1TakeL2 \/ T2TakeL2 \/ T2TakeL1
====
