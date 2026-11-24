---- MODULE MultiInvDistinctDepths ----
EXTENDS Naturals
VARIABLE x
Init == x = 0
Step == x < 5 /\ x' = x + 1
Stay == x = 5 /\ x' = 5
Next == Step \/ Stay
InvA == x # 2
InvB == x < 4
====
