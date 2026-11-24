---- MODULE MutexClean ----
VARIABLES p1, p2, lock
Init == p1 = "idle" /\ p2 = "idle" /\ lock = "free"
Req1 == p1 = "idle" /\ p1' = "wait" /\ UNCHANGED <<p2, lock>>
Enter1 == p1 = "wait" /\ lock = "free" /\ p1' = "crit" /\ lock' = "p1" /\ UNCHANGED p2
Exit1 == p1 = "crit" /\ p1' = "idle" /\ lock' = "free" /\ UNCHANGED p2
Req2 == p2 = "idle" /\ p2' = "wait" /\ UNCHANGED <<p1, lock>>
Enter2 == p2 = "wait" /\ lock = "free" /\ p2' = "crit" /\ lock' = "p2" /\ UNCHANGED p1
Exit2 == p2 = "crit" /\ p2' = "idle" /\ lock' = "free" /\ UNCHANGED p1
Next == Req1 \/ Enter1 \/ Exit1 \/ Req2 \/ Enter2 \/ Exit2
MutualExclusion == ~(p1 = "crit" /\ p2 = "crit")
====
