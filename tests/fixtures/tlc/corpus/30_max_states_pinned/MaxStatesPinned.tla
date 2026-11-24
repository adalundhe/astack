---- MODULE MaxStatesPinned ----
EXTENDS Naturals
VARIABLE id
Init == id = 0
Decoy == id = 0 /\ id' \in 1..13
P1 == id = 0 /\ id' = 14
P2 == id = 14 /\ id' = 15
P3 == id = 15 /\ id' = 16
P4 == id = 16 /\ id' = 17
Stay == id \in (1..13) \cup {17} /\ id' = id
Next == Decoy \/ P1 \/ P2 \/ P3 \/ P4 \/ Stay
PinnedInv == id # 17
====
